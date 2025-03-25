import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class Step(models.Model):
    _inherit = 'kw.chatbot.step'

    select_flow = fields.Selection(
        selection_add=[('sale', 'Sale')],
        ondelete={'sale': 'cascade'}, )
    operation_sale = fields.Selection([
        ('input_quantity', 'Input quantity'),
        ('send_message', 'Send message'),
        ('input_shipping_address', 'Input shipping address'),
        ('standard', 'Standard'), ],
        default='standard', )
    product_id = fields.Many2one(
        'product.product', )
    # category
    not_use_category = fields.Boolean(default=False)
    template_message_category = fields.Text(
        translate=True, default='Choose category')
    model_category_id = fields.Many2one(
        'ir.model',
        default=lambda self: self.env.ref('product.model_product_category').id)
    model_category_name = fields.Char(
        related='model_category_id.model', )
    filter_category_domain = fields.Char()
    # product
    use_img_product = fields.Boolean(default=False, string='Use image in select product')
    message_product_name = fields.Text(compute='_compute_message_product_name', )
    design_product_name_id = fields.One2many(
        comodel_name='kw.message.notification.line',
        inverse_name='design_product_name_id', )
    model_product_id = fields.Many2one(
        'ir.model',
        default=lambda self: self.env.ref('product.model_product_product').id)
    model_product_name = fields.Char(
        related='model_product_id.model', )
    filter_product_domain = fields.Char()
    message_back_to_product = fields.Text(translate=True,
                                          default='Back to product')
    # quantity
    message_quantity = fields.Text(compute='_compute_message_quantity', )
    design_message_quantity_id = fields.One2many(
        comodel_name='kw.message.notification.line',
        inverse_name='design_message_quantity_id', )
    button_name_enter_quantity = fields.Char(translate=True,
                                             default='Enter quantity')
    # cart
    notification_cart_id = fields.Many2one(
        'kw.chatbot.notification', )
    name_button_cart = fields.Char(translate=True,
                                   default='Cart')
    # add to cart
    notification_add_to_card = fields.Text(translate=True,
                                           default='Product added to cart')
    button_name_back_to_category = fields.Text(translate=True,
                                               default='Back to category')
    message_confirm_order = fields.Text(translate=True,
                                        default='Confirm order')
    button_name_add_to_cart = fields.Text(translate=True,
                                          default='Add to cart')
    notification_after_clear_cart = fields.Text(translate=True,
                                                default='Cart cleared')
    clear_cart_name_button = fields.Char(translate=True, default='Clear cart')
    button_name_after_confirm_order = fields.Text(
        translate=True,
        default='Your order is confirmed')
    # input data for shipping
    message_input_data_shipping = fields.Text(
        translate=True,
        default='Input your data for shipping in format: name, phone, address.'
                ' Example: John, +380123456789,'
                ' New York, 5th Avenue, 1. In one message')
    # url for payment
    not_use_payment_url = fields.Boolean(default=False)
    message_payment_url = fields.Text(translate=True, default='Payment url')
    button_name_payment_url = fields.Char(translate=True, default='Payment')
    # delivery
    not_use_delivery = fields.Boolean(default=False)
    message_select_delivery = fields.Text(translate=True,
                                          default='Select delivery')
    # tags sale order
    tag_ids = fields.Many2many(
        'crm.tag', string='Tags', relation='kw_chatbot_sale_tag_rel', )

    def _compute_message_product_name(self):
        self.ensure_one()
        message = ''
        # flake8: noqa: E501
        for line in self.design_product_name_id.sorted(key=lambda r: r.sequence):
            message += line.part_message if line.part_message else ' '
        self.message_product_name = message

    def _compute_message_quantity(self):
        self.ensure_one()
        message = ''
        # flake8: noqa: E501
        for line in self.design_message_quantity_id.sorted(key=lambda r: r.sequence):
            message += line.part_message if line.part_message else ' '
        self.message_quantity = message

    @api.onchange('select_flow')
    def onchange_select_flow_sale(self):
        # search in model kw.chatbot.step.alias
        # record with alias = '/sale'
        # if not found, create it
        alias = self.env['kw.chatbot.step.alias'].search(
            [('name', '=', '/sale')])
        if not alias:
            alias = self.env['kw.chatbot.step.alias'].create(
                {'name': '/sale'})  # TODO: recreate alias
        self.alias_ids = alias
