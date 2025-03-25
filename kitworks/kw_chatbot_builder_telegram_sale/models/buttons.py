import logging
from odoo import models, fields

_logger = logging.getLogger(__name__)


class StepTelegramButton(models.Model):
    _inherit = 'kw.chatbot.step.telegram.button'

    state = fields.Selection(
        selection_add=[('sale', 'Sale')], ondelete={'sale': 'set default'})
    type_sale = fields.Selection(
        selection=[
            ('choose_category', 'Choose category'),
            ('choose_product', 'Choose product'),
            ('choose_quantity', 'Choose quantity'),
            ('add_to_cart', 'Add to cart'),
            ('remove_from_cart', 'Remove from cart'),
            ('show_cart', 'Show cart'),
            ('confirm_order', 'Confirm order'), ],
        default='choose_category', )
    category_id = fields.Many2one(
        'product.category', )
    product_id = fields.Many2one(
        'product.product', )
