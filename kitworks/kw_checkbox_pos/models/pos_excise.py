import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class PosExcise(models.Model):
    _name = 'kw.pos.excise'

    name = fields.Char(name='Excise Name', required=True)
    order_line_id = fields.Many2one(comodel_name='pos.order.line')
