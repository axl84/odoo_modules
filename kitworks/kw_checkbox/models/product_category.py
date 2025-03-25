import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class CheckboxProductCategory(models.Model):
    _name = 'kw.checkbox.product.category'
    _description = 'Checkbox product category'

    name = fields.Char(
        string='Product Category Name', )
    active = fields.Boolean(
        default=True, )
