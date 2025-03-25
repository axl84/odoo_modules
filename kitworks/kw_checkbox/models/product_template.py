import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    kw_checkbox_uktzed = fields.Char(
        string='UKTZED', )
    kw_checkbox_header = fields.Char(
        string='Receipt header', )
    kw_checkbox_footer = fields.Char(
        string='Receipt footer', )
    kw_checkbox_product_category_id = fields.Many2one(
        comodel_name='kw.checkbox.product.category',
        default=lambda self: self.env['kw.checkbox.product.category'].search(
            [('name', '=', 'Default Category')]),
        string='Product Category', )
