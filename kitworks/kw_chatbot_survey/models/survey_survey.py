# flake8: noqa: E501
import logging

from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class Survey(models.Model):
    _inherit = 'survey.survey'

    kw_step_ids = fields.One2many(
        comodel_name='kw.chatbot.step', inverse_name='survey_id', )
    message_start_survey = fields.Char(
        translate=True,
        default='Press the button to start the survey')
    message_end_survey = fields.Char(
        translate=True,
        default='Thank you for your participation')
    kw_message_error = fields.Char(
        translate=True, string='Message Error',
        default='Sorry, something went wrong')
    kw_close_quiz_button_name = fields.Char(
        translate=True, string='Close Quiz Button',
        default='Close Quiz')
    kw_default_value_ids = fields.One2many(
        comodel_name='kw.survey.survey.default.value',
        inverse_name='survey_id', )


class SurveyQuestion(models.Model):
    _inherit = 'survey.question'

    DEFAULT_PYTHON_CODE = """# Available variables:
    #  - env: Odoo Environment on which the action is triggered
    #  - model: Odoo Model of the record on which the action is triggered; is a void recordset
    #  - record: record on which the action is triggered; may be void
    #  - records: recordset of all records on which the action is triggered in multi-mode; may be void
    #  - time, datetime, dateutil, timezone: useful Python libraries
    #  - float_compare: Odoo function to compare floats based on specific precisions
    #  - log: log(message, level='info'): logging function to record debug information in ir.logging table
    #  - UserError: Warning Exception to use with raise
    #  - Command: x2Many commands namespace
    #  - sender_user: user who sent the message
    #  - sender_partner: user's partner
    # To return an action, assign: action = {...}\n\n\n\n"""

    is_search = fields.Boolean(
        default=False, string='Search')
    is_update_suggested_answer = fields.Boolean(
        default=True, string="Update Suggested Answer")
    kw_search_model_id = fields.Many2one(
        comodel_name='ir.model', string='Search Model',
        compute_sudo=True,
        compute='_compute_search_model',
        index=True, ondelete='cascade', )
    kw_search_field_id = fields.Many2one(
        comodel_name='ir.model.fields', string='Search Field',
        domain="[('model_id', '=', kw_search_model_id)]",
        ondelete='cascade', )
    kw_search_message = fields.Text(
        string='Unsuccessful Search Message',
        default='Nothing found', translate=True)
    kw_button_search_message = fields.Text(
        string='Button Search Message',
        default='Try Again', translate=True)
    kw_button_action_message = fields.Text(
        string='Action Search Message',
        default='Next Quiz', translate=True)
    kw_field_search_message = fields.Text(
        string='Search Message',
        default='Search by', translate=True)
    kw_field_waiting_message = fields.Text(
        string='Search Message',
        default='Please wait', translate=True)
    code = fields.Text(
        string='Python Code', groups='base.group_system',
        default=DEFAULT_PYTHON_CODE,
        help="Write Python code that the action will execute. Some variables "
             "are available for use; help about python expression "
             "is given in the help tab.")
    kw_suggested_update_date = fields.Datetime(
        default=fields.Datetime.now)

    @api.onchange('kw_entity_field_id')
    def onchange_kw_entity_field(self):
        for obj in self:
            if obj.kw_entity_field_id and not obj.kw_entity_field_id.relation:
                obj.is_search = False

    @api.onchange('kw_entity_field_id')
    def _compute_search_model(self):
        for obj in self:
            obj.kw_search_model_id = False
            if obj.kw_entity_field_id and obj.kw_entity_field_id.relation:
                model_id = self.env['ir.model'].search([
                    ('model', '=', obj.kw_entity_field_id.relation)], limit=1)
                obj.kw_search_model_id = model_id.id

    def update_value_suggested(self):
        self.ensure_one()
        domain = []
        if self.kw_filter_domain:
            domain = safe_eval(self.kw_filter_domain)
        value = []
        if self.kw_entity_field_id and self.question_type in \
                ['simple_choice', 'multiple_choice'] and \
                self.kw_entity_field_id.ttype in ['many2one', 'many2many']:
            model_name = self.kw_entity_field_id.relation
            for x in self.env[model_name].search(domain).filtered(
                    lambda k: k.write_date > self.kw_suggested_update_date):
                if not self.suggested_answer_ids.filtered(
                        lambda y: y.value == x.name):
                    value.append([0, 0, {
                        'value': x.name, 'kw_survey_answer_value': x.id}])
            self.suggested_answer_ids = value
            self.kw_suggested_update_date = fields.Datetime.now()

class DefaultValue(models.Model):
    _name = 'kw.survey.survey.default.value'

    survey_id = fields.Many2one(
        comodel_name='survey.survey',
        string='Survey', ondelete='cascade', )
    kw_model_id = fields.Many2one(
        comodel_name='ir.model',
        related='survey_id.kw_entity_model_id')
    col1 = fields.Many2one(
        comodel_name='ir.model.fields', string='Field',
        domain="[('model_id', '=', kw_model_id)]",
        required=True, ondelete='cascade', )
    evaluation_type = fields.Selection(
        [('value', 'Value'),
         ('reference', 'Reference'),
         ('equation', 'Python expression'),
         ('partner', 'Fill partner')],
        default='value', change_default=True, required=True, )
    resource_ref = fields.Reference(
        string='Record', selection='_selection_target_model',
        compute='_compute_resource_ref', inverse='_inverse_set_resource_ref', )
    value = fields.Text()

    @api.model
    def _selection_target_model(self):
        return [(model.model, model.name) for model in
                self.env['ir.model'].sudo().search([])]

    @api.depends('col1.relation', 'value', 'evaluation_type')
    def _compute_resource_ref(self):
        for line in self:
            if line.evaluation_type in ['reference', 'value'] and line.col1 \
                    and line.col1.relation:
                value = line.value or ''
                try:
                    value = int(value)
                    if not self.env[line.col1.relation].browse(value).exists():
                        record = list(
                            self.env[line.col1.relation]._search([], limit=1))
                        value = record[0] if record else 0
                except ValueError:
                    record = list(
                        self.env[line.col1.relation]._search([], limit=1))
                    value = record[0] if record else 0
                line.resource_ref = '%s,%s' % (line.col1.relation, value)
            else:
                line.resource_ref = False

    @api.onchange('resource_ref')
    def _inverse_set_resource_ref(self):
        for line in self.filtered(
                lambda x: x.evaluation_type == 'reference'):
            if line.resource_ref:
                line.value = str(line.resource_ref.id)

    @api.constrains('col1', 'evaluation_type')
    def _raise_many2many_error(self):
        if self.filtered(
                lambda x: x.col1.ttype == 'many2many' and
                x.evaluation_type == 'reference'):
            raise ValidationError(
                _('many2many fields cannot be evaluated by reference'))

    @api.onchange('evaluation_type')
    def _onchange_evaluation_type(self):
        for line in self:
            if line.evaluation_type == 'partner':
                if line.col1.relation not in ['res.partner', 'res.users']:
                    line.evaluation_type = 'value'
                else:
                    line.resource_ref = False
                    line.value = False


class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    kw_chatbot_partner_id = fields.Many2one(
        comodel_name='res.partner',
        ondelete='cascade', )
    kw_conversation_id = fields.Many2one(
        comodel_name='kw.chatbot.conversation', )

    def kw_prepare_entity_data(self):
        data = super().kw_prepare_entity_data()
        self.ensure_one()
        for line in self.survey_id.kw_default_value_ids:
            if line.resource_ref:
                data[line.col1.name] = line.resource_ref.id
            elif line.evaluation_type == 'partner':
                try:
                    partner_id = self.kw_chatbot_partner_id.id
                    if line.col1.relation == 'res.users':
                        user = self.env['res.users'].search([
                            ('partner_id', '=', partner_id)], limit=1)
                        if user:
                            data[line.col1.name] = user.id
                    else:
                        data[line.col1.name] = partner_id
                except ValueError:
                    data[line.col1.name] = False
            elif line.evaluation_type == 'equation':
                try:
                    conversation = self.kw_conversation_id
                    eval_context = conversation._get_eval_context()
                    eval_context['record'] = conversation
                    eval_context['model'] = conversation._name
                    eval_context['env'] = self.env
                    expr = safe_eval(line.value, eval_context)
                    data[line.col1.name] = expr
                except ValueError:
                    data[line.col1.name] = False
            else:
                data[line.col1.name] = line.value
        return data
