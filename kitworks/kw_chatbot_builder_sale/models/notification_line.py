import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class MessageNotificationLine(models.Model):
    _inherit = 'kw.message.notification.line'

    design_product_name_id = fields.Many2one(
        'kw.chatbot.step', )
    model_product_id = fields.Many2one(
        'ir.model',
        default=lambda self: self.env.ref('product.model_product_product').id)
    model_product_name = fields.Char(
        related='model_product_id.model', )
    design_message_quantity_id = fields.Many2one(
        'kw.chatbot.step', )
