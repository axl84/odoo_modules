import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class Survey(models.Model):
    _inherit = 'survey.survey'

    kw_is_lead_creator = fields.Boolean(
        string='Lead creator', compute='_compute_kw_is_lead_creator', )
    kw_lead_salesperson_id = fields.Many2one(
        comodel_name='res.users', string='Salesperson', )
    kw_lead_sales_team_id = fields.Many2one(
        comodel_name='crm.team', string='Sales Team', )

    def _compute_kw_is_lead_creator(self):
        for obj in self:
            obj.kw_is_lead_creator = obj.kw_entity_model_id.model == 'crm.lead'
