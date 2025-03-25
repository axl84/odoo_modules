import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class Sender(models.Model):
    _inherit = 'kw.chatbot.sender'

    telegram_id = fields.Char()

    telegram_is_bot = fields.Boolean()

    telegram_first_name = fields.Char()

    telegram_last_name = fields.Char()

    telegram_username = fields.Char()

    telegram_language_code = fields.Char()

    @api.model
    def get_or_create(self, messenger, **kwargs):
        if messenger.provider != 'telegram':
            return super().get_or_create(messenger, **kwargs)
        from_user = kwargs.get('from_user')
        if not from_user:
            raise ValueError('Cant process message: "from_user" not provided')
        sender = self.sudo().search([
            ('telegram_id', '=', from_user.id)], limit=1)
        if not sender:
            sender = self.sudo().create({
                'name': '{} {}'.format(
                    from_user.first_name, from_user.last_name),
                'messenger_id': messenger.id,
                'telegram_id': from_user.id,
                'telegram_is_bot': from_user.is_bot,
                'telegram_first_name': from_user.first_name,
                'telegram_last_name': from_user.last_name,
                'telegram_username':
                    from_user.username if from_user.username else '',
                'telegram_language_code': from_user.language_code, })
        return sender
