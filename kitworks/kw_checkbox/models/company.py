import logging

from odoo import models, fields, _

_logger = logging.getLogger(__name__)


class Company(models.Model):
    _inherit = 'res.company'

    kw_checkbox_mode = fields.Selection(
        default='prod', string='CheckBox mode', selection=[
            ('test', _('Test')), ('prod', _('Production')), ], )
    kw_checkbox_salesperson_info = fields.Char(
        help="Official information about salesperson, "
             "which will display in receipt")
    kw_checkbox_rounding_text = fields.Char(string='Rounding Text in Receipt')
