import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class Sender(models.Model):
    _inherit = 'kw.chatbot.sender'

    viber_id = fields.Char()

    viber_country = fields.Char()

    viber_avatar = fields.Char()

    viber_language_code = fields.Char()

    @api.model
    def get_or_create(self, messenger, **kwargs):
        if messenger.provider != 'viber':
            return super().get_or_create(messenger, **kwargs)
        viber_sender = kwargs.get('sender')
        if not viber_sender:
            raise ValueError('Cant process message: "sender" not provided')
        sender = self.sudo().search([
            ('viber_id', '=', viber_sender.get('id'))], limit=1)
        if not sender:
            sender = self.sudo().create({
                'name': viber_sender.get('name'),
                'messenger_id':  messenger.id,
                'viber_id': viber_sender.get('id'),
                'viber_country': viber_sender.get('country'),
                'viber_avatar': viber_sender.get('avatar'),
                'viber_language_code': viber_sender.get('language'), })
        return sender
