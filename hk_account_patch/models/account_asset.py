
import calendar
from odoo import api, fields, models, _


class AccountAsset(models.Model):
    _inherit = 'account.asset.asset'

    date = fields.Date(string='Date', required=True, readonly=False,
                       default=fields.Date.context_today)
    
    category_id = fields.Many2one(readonly=False)
    company_id = fields.Many2one(readonly=False)
    currency_id = fields.Many2one(readonly=False)
    display_name = fields.Char(readonly=False)
    method = fields.Selection(readonly=False)
    method_end = fields.Date(readonly=False)
    method_number = fields.Integer(readonly=False)
    method_period = fields.Integer(readonly=False)
    method_progress_factor = fields.Float(readonly=False)
    method_time = fields.Selection(readonly=False)
    name = fields.Char(readonly=False)
    partner_id = fields.Many2one(readonly=False)
    prorata = fields.Boolean(readonly=False)
    salvage_value = fields.Float(readonly=False)
    value = fields.Float(readonly=False)
    value_residual = fields.Float(readonly=False)






