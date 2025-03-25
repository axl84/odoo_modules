import logging

from odoo import models, fields, _

_logger = logging.getLogger(__name__)


class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    kw_crm_lead_id = fields.Many2one(
        comodel_name='crm.lead', )

    def kw_prepare_entity_data(self):
        data = super().kw_prepare_entity_data()
        if 'name' not in data and self.survey_id.kw_is_lead_creator:
            data['name'] = _('{survey_name} {user_input_id}').format(
                survey_name=self.survey_id.title,
                user_input_id=self.id, )
        if self.survey_id.kw_lead_salesperson_id:
            data['user_id'] = self.survey_id.kw_lead_salesperson_id.id
        if self.survey_id.kw_lead_sales_team_id:
            data['team_id'] = self.survey_id.kw_lead_sales_team_id.id
        return data

    def _mark_done(self):
        result = super()._mark_done()
        for obj in self:
            if not obj.survey_id.kw_is_lead_creator:
                continue
            obj.kw_crm_lead_id = obj.kw_entity_res_id
            entity = self.env[obj.kw_entity_model_id.model].sudo().browse(
                self.kw_entity_res_id)
            entity.kw_survey_user_input_id = obj.id
        return result


class SurveyUserInputLine(models.Model):
    _inherit = 'survey.user_input.line'

    kw_crm_lead_id = fields.Many2one(
        comodel_name='crm.lead', related='user_input_id.kw_crm_lead_id',
        store=True, )
