import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class Sender(models.Model):
    _inherit = 'kw.chatbot.sender'

    instagram_id = fields.Char()

    @api.model
    def get_or_create(self, messenger, **kwargs):
        if messenger.provider != 'instagram':
            return super().get_or_create(messenger, **kwargs)
        sender_id = kwargs.get('sender')
        name = sender_id
        if isinstance(sender_id, dict):
            if sender_id.get('name'):
                name = sender_id.get('name')
                sender_id = sender_id.get('id')
            if isinstance(sender_id, dict) and sender_id.get('first_name'):
                name = '{} {}'.format(
                    sender_id.get('first_name'), sender_id.get('last_name'))
                sender_id = sender_id.get('id')
        if not sender_id:
            raise ValueError('Cant process message: "sender" not provided')
        instagram_sender = self.sudo().search([
            ('instagram_id', '=', sender_id)], limit=1)
        if not instagram_sender:
            instagram_sender = self.sudo().create({
                'messenger_id': messenger.id,
                'name': name,
                'instagram_id': sender_id, })
        return instagram_sender
