import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class CheckboxOfflineCode(models.Model):
    _name = 'kw.checkbox.offline.code'
    _description = 'Checkbox offline code'

    serial_id = fields.Char(
        readonly=True, )
    fiscal_code = fields.Char(
        readonly=True, )
    active = fields.Boolean(
        default=True, readonly=True, )
    datetime_created_at = fields.Datetime(
        string='Create at', readonly=True, )
    cash_register_id = fields.Many2one(
        comodel_name='kw.checkbox.cash.register', readonly=True, )
