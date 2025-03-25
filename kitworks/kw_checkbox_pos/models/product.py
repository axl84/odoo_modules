import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)\



class PosExcise(models.Model):
    _name = 'product.product'
    _inherit = 'product.product'

    is_excise_product = fields.Boolean()
