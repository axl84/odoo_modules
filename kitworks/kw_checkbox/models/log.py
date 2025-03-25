import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class CheckboxLog(models.Model):
    _name = 'kw.checkbox.log'
    _description = 'Checkbox log'
    _order = 'create_date DESC'

    name = fields.Char(
        string='URL', )
    json = fields.Text()

    params = fields.Text()

    headers = fields.Text()

    error = fields.Text()

    response = fields.Text()

    method = fields.Char()

    code = fields.Char()

    cashier = fields.Char()

    cash_register = fields.Char()
