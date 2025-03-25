import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class CheckboxCategory(models.Model):
    _name = 'kw.checkbox.category'
    _description = 'CheckBox Category'

    pos_config_id = fields.Many2one(
        comodel_name='pos.config',)
    kw_checkbox_product_category_id = fields.Many2one(
        comodel_name='kw.checkbox.product.category',
        default=lambda self: self.env['kw.checkbox.product.category'].search(
            [('name', '=', 'Default Category')]),
        string='Product Category', required=True, )
    kw_checkbox_cash_register_id = fields.Many2one(
        comodel_name='kw.checkbox.cash.register',
        string='Cash register', required=True, )
    kw_checkbox_organization_id = fields.Many2one(
        comodel_name='kw.checkbox.organization',
        related="kw_checkbox_cash_register_id.organization_id",
        string='Organization', readonly=True, required=True, )
