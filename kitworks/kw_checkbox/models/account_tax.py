import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class AccountTax(models.Model):
    _inherit = 'account.tax'

    kw_checkbox_tax_ids = fields.Many2many(
        comodel_name='kw.checkbox.tax', )
