import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class Sender(models.Model):
    _inherit = 'kw.chatbot.sender'

    whatsapp_id = fields.Char()

    whatsapp_name = fields.Char()

    @api.model
    def get_or_create(self, messenger, **kwargs):
        if messenger.provider != 'whatsapp':
            return super().get_or_create(messenger, **kwargs)
        w_sender = kwargs.get('sender')
        wa_id = w_sender.get('wa_id')
        if not wa_id:
            raise ValueError('Cant process message: "wa_id" not provided')
        sender = self.sudo().search([
            ('whatsapp_id', '=', wa_id)], limit=1)
        if not sender:
            sender = self.sudo().create({
                'name': w_sender.get('profile').get('name'),
                'messenger_id': messenger.id,
                'whatsapp_name': w_sender.get('profile').get('name'),
                'whatsapp_id': wa_id, })
        return sender
