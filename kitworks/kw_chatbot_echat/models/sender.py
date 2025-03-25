import logging

from odoo import models, fields, api, exceptions, _

_logger = logging.getLogger(__name__)


class Sender(models.Model):
    _inherit = 'kw.chatbot.sender'

    echat_sender_id = fields.Char()

    echat_username = fields.Char()

    echat_mobile_phone = fields.Char()

    @api.model
    def get_or_create(self, messenger, **kwargs):
        if messenger.provider != 'echat':
            return super().get_or_create(messenger, **kwargs)
        sender = self.sudo().search([
            ('echat_mobile_phone', '=', str(kwargs['sender'].get('phone')))],
            limit=1)
        if not sender:
            sender_name = (kwargs['sender'].get('name').strip()
                           or kwargs['sender'].get('username')
                           or f"Unknown_{kwargs['sender'].get('id')}")

            sender = self.sudo().create({
                'name': sender_name,
                'echat_sender_id': kwargs['sender'].get('id'),
                'echat_username': sender_name,
                'echat_mobile_phone': kwargs['sender'].get('phone'),
                'messenger_id': messenger.id, })
        return sender

    def aprove_sender(self):
        for obj in self:
            if obj.provider == 'echat':
                raise exceptions.UserError(_(
                    'This sender (E-Chat) cannot become an operator'))
        return super().aprove_sender()

    def reject_sender(self):
        for obj in self:
            if obj.provider == 'echat':
                raise exceptions.UserError(_(
                    'This sender (E-Chat) cannot become an operator'))
        return super().aprove_sender()
