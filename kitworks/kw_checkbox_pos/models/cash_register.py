import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class CheckboxCashRegister(models.Model):
    _inherit = 'kw.checkbox.cash.register'

    count_offline_codes = fields.Integer()
    min_count_codes = fields.Integer(
        default=20, string='Min offline codes', required=True, )
