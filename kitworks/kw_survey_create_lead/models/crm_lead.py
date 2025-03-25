import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class Lead(models.Model):
    _inherit = 'crm.lead'

    kw_survey_user_input_id = fields.Many2one(
        comodel_name='survey.user_input', string='Survey user input', )
    kw_user_input_line_ids = fields.One2many(
        comodel_name='survey.user_input.line', inverse_name='kw_crm_lead_id',
        string='Answers', )
