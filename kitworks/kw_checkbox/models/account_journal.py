

import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class CheckboxAccountJournal(models.Model):
    _inherit = 'account.journal'

    kw_checkbox_is_register_receipt = fields.Boolean(
        default=False, string='Register Checkbox receipt')
    kw_checkbox_organization_id = fields.Many2one(
        comodel_name='kw.checkbox.organization', string='Organization', )
    kw_checkbox_payment_method_type = fields.Selection(
        [('0', 'Cash'), ('1', 'Cashless'), ('2', 'Other')],
        string='Payment Method Type',
        default='0',
    )
    kw_checkbox_payment_method_name = fields.Char(
        string='Payment Method Name',
        help="The Payment method's name should be specified "
             "according to legal regulations.",
    )
