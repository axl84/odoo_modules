import logging

from odoo import models, fields, _

_logger = logging.getLogger(__name__)


class Survey(models.Model):
    _inherit = 'survey.survey'

    kw_facebook_form_id = fields.Char(
        readonly=True, )
    kw_facebook_page_id = fields.Many2one(
        comodel_name='kw.facebook.page',
        string='Facebook Page', ondelete='cascade', )
    facebook_lead_count = fields.Integer(
        "Leads", compute="_compute_facebook_lead")
    is_facebook_forms = fields.Boolean(
        default=False, )
    is_active_lead_form = fields.Boolean(
        default=True, )

    def _compute_facebook_lead(self):
        for obj in self:
            input_ids = obj.user_input_ids.filtered(
                lambda x: x.kw_entity_model == 'crm.lead')
            ids = self.env['crm.lead'].sudo().search([
                ('kw_survey_user_input_id', 'in', input_ids.ids)]).ids
            obj.write({'facebook_lead_count': len(ids)})

    def get_facebook_lead(self):
        if self.kw_facebook_page_id:
            self.kw_facebook_page_id.get_facebook_lead_survey(
                facebook_survey_forms=self)

    def facebook_crm_lead_action(self):
        input_ids = self.user_input_ids.filtered(
            lambda x: x.kw_entity_model == 'crm.lead')
        ids = self.env['crm.lead'].sudo().search([
            ('kw_survey_user_input_id', 'in', input_ids.ids)]).ids
        return {
            'type': 'ir.actions.act_window',
            'name': _("Leads"),
            'res_model': 'crm.lead',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('id', 'in', ids), ], }


class SurveyQuestionTemplate(models.Model):
    _inherit = 'survey.question'

    kw_facebook_question_id = fields.Char(
        readonly=True, )
    kw_facebook_question_key = fields.Char(
        readonly=True, )
    is_facebook_question = fields.Boolean(
        default=False, )


class SurveyInput(models.Model):
    _inherit = 'survey.user_input'

    kw_facebook_lead_id = fields.Char(
        readonly=True, )
