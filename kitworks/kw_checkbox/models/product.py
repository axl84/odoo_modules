import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class Product(models.Model):
    _inherit = 'product.product'

    def kw_checkbox_good(self):
        self.ensure_one()
        return {
            'code': self.id, 'name': self.name, 'barcode': self.barcode,
            'price': self.price * 100,
            'header': self.product_tmpl_id.kw_checkbox_header,
            'footer': self.product_tmpl_id.kw_checkbox_footer,
            'uktzed': self.product_tmpl_id.kw_checkbox_uktzed, }


class ProductCategory(models.Model):
    _inherit = 'product.category'

    kw_checkbox_product_category_id = fields.Many2one(
        comodel_name='kw.checkbox.product.category',
        string='Product Category', )
