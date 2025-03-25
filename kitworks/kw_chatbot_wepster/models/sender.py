import logging

from odoo import models, fields, api, exceptions, _

_logger = logging.getLogger(__name__)


class Sender(models.Model):
    _inherit = 'kw.chatbot.sender'

    wepster_id = fields.Char()

    wepster_is_bot = fields.Boolean()

    wepster_username = fields.Char()

    wepster_email = fields.Char()

    wepster_userId = fields.Char()

    wepster_channel_id = fields.Many2one(
        comodel_name='kw.chatbot.wepster.channels', readonly=True, )

    @api.model
    def get_or_create(self, messenger, **kwargs):
        if messenger.provider != 'wepster':
            return super().get_or_create(messenger, **kwargs)
        data = kwargs['sender']
        customer = data.get('eventData').get('customer')
        self.env['kw.chatbot.messenger'].search([
            ('provider', '=', 'wepster')],
            limit=1).get_wepster_channels()
        channel = self.env['kw.chatbot.wepster.channels'].search([
            ('wepster_channel_id', '=', data.get('applicationId'))])
        sender = self.sudo().search([
            ('wepster_id', '=', data.get('eventData').get('chat_id'))],
            limit=1)
        if not sender:
            sender = self.sudo().create({
                'name': customer.get('name'),
                'wepster_channel_id': channel.id if channel else False,
                'messenger_id': messenger.id,
                'wepster_id': customer.get('id'),
                'wepster_username': customer.get('name'),
                'wepster_email': customer.get('email'),
                'wepster_userId': customer.get('userId'), })
        return sender

    def aprove_sender(self):
        for obj in self:
            if obj.provider == 'wepster':
                raise exceptions.UserError(_(
                    'This sender (Wepster) cannot become an operator'))
        return super().aprove_sender()

    def reject_sender(self):
        for obj in self:
            if obj.provider == 'wepster':
                raise exceptions.UserError(_(
                    'This sender (Wepster) cannot become an operator'))
        return super().aprove_sender()
