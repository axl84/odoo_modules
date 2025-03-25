import logging
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, exceptions, _
from odoo.addons.kw_graph_api.models.graph_api import FacebookGraphApi

_logger = logging.getLogger(__name__)


class FacebookPage(models.Model):
    _inherit = 'kw.facebook.page'

    is_lead_form = fields.Boolean(
        default=False, )
    lead_form_permission = fields.Text(
        readonly='True',
        default='Create and manage ads for your Page; '
                'Read content posted on the Page; '
                'Access leads for your Pages', )
    facebook_survey_ids = fields.One2many(
        comodel_name='survey.survey',
        inverse_name='kw_facebook_page_id', )
    form_lead_limit = fields.Integer(
        default=10)
    is_day_to_inactive = fields.Boolean(
        default=False, string='Inactive Form')
    day_to_inactive = fields.Integer(
        default=7)
    is_leadgen_request_limit = fields.Boolean(
        default=False, )

    leadgen_limit_time = fields.Datetime()

    def facebook_leadgen_request_limit(self):
        current_time = fields.Datetime.now()
        if self.leadgen_limit_time and self.is_leadgen_request_limit:
            limit_time = fields.Datetime.from_string(self.leadgen_limit_time)
            if current_time >= limit_time + timedelta(hours=1):
                self.is_leadgen_request_limit = False
        return self.is_leadgen_request_limit

    def facebook_form_lead_process_call(self, data):
        self.ensure_one()
        self.facebook_create_leadgen(data)

    def _facebook_create_lead_survey(self):
        survey_form = self.env['kw.facebook.page'].sudo().search([
            ('active', '=', True), ('net_object', '=', 'page'),
            ('is_lead_form', '=', True)])
        if survey_form:
            for form in survey_form:
                form.get_facebook_lead_form()
                today = date.today()
                unix_today = today.strftime("%s")
                filtering_params = [{
                    'field': 'time_created', 'operator': 'GREATER_THAN',
                    'value': unix_today}]
                form.get_facebook_lead_survey(
                    filtering_params=filtering_params)

    @api.onchange('is_lead_form')
    def onchange_is_lead_form(self):
        message = {
            'title': _("Warning!"),
            'message': self.subscribe_msg
        }
        return {'warning': message}

    def get_permission(self):
        permission = super().get_permission()
        if self.is_lead_form:
            permission = '{},{}'.format(
                permission,
                'leads_retrieval,pages_manage_ads,pages_read_engagement')
        return permission

    def lead_form_webhook_action(self):
        if not self.is_facebook_webhook \
                or not self.facebook_app_id.page_webhook_token:
            raise exceptions.ValidationError(
                _('The webhook cannot be configured!'
                  ' Go to the settings of the Facebook App'))
        context = {
            'default_facebook_app_id': self.facebook_app_id.id,
            'default_facebook_object': 'page',
            'default_facebook_fields': 'leadgen',
            'default_callback_url':
                self.facebook_app_id.page_copy_url,
            'default_verify_token':
                self.facebook_app_id.page_verify_token, }
        webhook = self.env['facebook.webhook.wizard'].sudo().with_context(
            **context).create({})
        return webhook.facebook_update_webhook()

    # pylint: disable=R1710
    def get_facebook_lead_form(self):
        if self.facebook_leadgen_request_limit():
            return False
        params = {
            'access_token': self.access_token,
            'fields': 'leadgen_forms'}
        forms = FacebookGraphApi().get_facebook_graph(
            url='/me', params=params)
        if forms.get('data'):
            forms = forms['data'].get('leadgen_forms')
            if forms:
                for form in forms.get('data'):
                    self.facebook_get_or_create_survey(form.get('id'))
        if forms.get('error'):
            error = forms['error'].get('error')
            code = error.get('code') if error else 0
            if code == 80005:
                self.is_leadgen_request_limit = True
                self.leadgen_limit_time = fields.Datetime.now()

    def facebook_get_or_create_survey(self, form_id):
        params = {
            'access_token': self.access_token,
            'fields': 'id,name,questions'}
        forms = FacebookGraphApi().get_facebook_graph(
            url='/{}'.format(form_id), params=params)
        if forms.get('data'):
            forms = forms['data']
            facebook_form_id = forms.get('id')
            survey_id = self.env['survey.survey'].search([
                ('kw_facebook_form_id', '=', facebook_form_id),
                ('kw_facebook_page_id', '=', self.id)])
            model = self.env['ir.model'].sudo().search(
                [('model', '=', 'crm.lead')], limit=1)
            q_list = []
            if not survey_id:
                survey_id = survey_id.create({
                    'is_facebook_forms': True,
                    'title': forms.get('name'),
                    'kw_is_lead_creator': True,
                    'kw_is_entity_creator': True,
                    'kw_entity_model_id': model.id,
                    'kw_facebook_page_id': self.id,
                    'kw_facebook_form_id': facebook_form_id, })
                field_fb_id = self.env['ir.model.fields'].sudo().search([
                    ('name', '=', 'kw_facebook_page'),
                    ('model_id', '=', model.id)])
                fb_q = {
                    'is_facebook_question': True,
                    'title': 'Facebook Page ID',
                    'kw_entity_field_id': field_fb_id.id,
                    'kw_facebook_question_key': 'fb/{}'.format(self.id),
                    'survey_id': survey_id.id,
                    'question_type': 'char_box', }
                q_list.append(fb_q)
            for question in forms.get('questions'):
                facebook_question_id = question.get('id')
                question_id = self.env['survey.question'].search([
                    ('kw_facebook_question_id', '=',
                     facebook_question_id), ])
                if not question_id:
                    data = {
                        'is_facebook_question': True,
                        'title': question.get('label'),
                        'kw_facebook_question_key': question.get('key'),
                        'survey_id': survey_id.id,
                        'kw_facebook_question_id':
                            facebook_question_id,
                        'question_type': 'char_box', }
                    if question.get('type') == 'PHONE':
                        field_id = self.env['ir.model.fields'].sudo().search([
                            ('name', '=', 'kw_facebook_phone'),
                            ('model_id', '=', model.id)])
                        if field_id:
                            data.update({'kw_entity_field_id': field_id.id})
                    if question.get('type') == 'FULL_NAME':
                        field_id = self.env['ir.model.fields'].sudo().search([
                            ('name', '=', 'kw_facebook_name'),
                            ('model_id', '=', model.id)])
                        if field_id:
                            data.update({'kw_entity_field_id': field_id.id})
                    q_list.append(data)
            if q_list:
                self.env['survey.question'].create(q_list)
            return survey_id
        return False

    # pylint: disable=R1710
    def get_facebook_lead_survey(
            self, facebook_survey_forms=None, filtering_params=None):
        if self.facebook_leadgen_request_limit():
            return False
        params = {
            'access_token': self.access_token}
        if not facebook_survey_forms:
            facebook_survey_ids = self.env['survey.survey'].sudo().search(
                [('kw_facebook_page_id', '=', self.id)],
                order='create_date DESC', limit=self.form_lead_limit)
            facebook_survey_forms = facebook_survey_ids.filtered(
                lambda x: x.is_active_lead_form)
        if facebook_survey_forms:
            for facebook_survey in facebook_survey_forms:
                if self.is_day_to_inactive and self.day_to_inactive:
                    self.check_lead_form(
                        facebook_survey_id=facebook_survey)
                url = '/{}/leads'.format(
                    facebook_survey.kw_facebook_form_id)
                if filtering_params:
                    url = '{}?filtering={}'.format(url, filtering_params)
                leads = FacebookGraphApi().get_facebook_graph(
                    url='{}'.format(url), params=params)
                if leads.get('data'):
                    for lead in leads['data'].get('data'):
                        value = {
                            'form_id': facebook_survey.kw_facebook_form_id,
                            'leadgen_id': lead.get('id')}
                        self.facebook_create_leadgen(value=value)
                if leads.get('error'):
                    error = leads['error'].get('error')
                    code = error.get('code') if error else 0
                    if code == 80005:
                        self.is_leadgen_request_limit = True
                        self.leadgen_limit_time = fields.Datetime.now()

    def check_lead_form(self, facebook_survey_id):
        self.ensure_one()
        date_to_inactive = facebook_survey_id.create_date + relativedelta(
            days=self.day_to_inactive)
        if date_to_inactive <= fields.Datetime.now():
            facebook_survey_id.write({
                'is_active_lead_form': False})

    def user_input_for_facebook_page(self, survey_id, user_input):
        question_id = self.env['survey.question'].search([
            ('is_facebook_question', '=', True),
            ('kw_facebook_question_key', '=', 'fb/{}'.format(self.id)),
            ('title', '=', 'Facebook Page ID'),
            ('survey_id', '=', survey_id.id,)])
        self.env['survey.user_input.line'].sudo().create({
            'user_input_id': user_input.id,
            'question_id': question_id.id,
            'answer_type': question_id.question_type,
            'value_char_box': self.id})

    def facebook_create_leadgen(self, value):
        params = {
            'access_token': self.access_token, }
        ledgen_id = value.get('leadgen_id')
        respond = FacebookGraphApi().get_facebook_graph(
            url='/{}'.format(value.get('leadgen_id')), params=params)
        if respond.get('data'):
            survey = self.facebook_get_or_create_survey(value.get('form_id'))
            if survey:
                user_input = self.env['survey.user_input'].search([
                    ('survey_id', '=', survey.id),
                    ('kw_facebook_lead_id', '=', ledgen_id,)])
                if not user_input:
                    user_input = self.env['survey.user_input'].create({
                        'survey_id': survey.id,
                        'kw_facebook_lead_id': ledgen_id})
                    self.user_input_for_facebook_page(
                        survey_id=survey, user_input=user_input)
                    for question_field in respond['data'].get('field_data'):
                        question_id = self.env['survey.question'].search([
                            ('kw_facebook_question_key', '=',
                             question_field.get('name')),
                            ('survey_id', '=', survey.id,)])
                        self.env['survey.user_input.line'].create({
                            'user_input_id': user_input.id,
                            'question_id': question_id.id,
                            'answer_type': question_id.question_type,
                            'value_char_box': question_field.get('values')[0]})
                    user_input._mark_done()
