import logging

from odoo import models, fields, api, exceptions, _

_logger = logging.getLogger(__name__)


class Sender(models.Model):
    _inherit = 'kw.chatbot.sender'

    help_crunch_id = fields.Char()

    help_crunch_is_bot = fields.Boolean()

    help_crunch_username = fields.Char()

    help_crunch_email = fields.Char()

    help_crunch_userId = fields.Char()

    hc_token = fields.Char()

    help_crunch_channel_id = fields.Many2one(
        comodel_name='kw.chatbot.helpcrunch.channels', readonly=True, )

    # pylint: disable=R1710
    @api.model
    def get_or_create(self, messenger, **kwargs):
        if messenger.provider != 'help_crunch':
            return super().get_or_create(messenger, **kwargs)
        customer = kwargs['sender'].get('customer')
        message = kwargs['sender'].get('message')
        self.env['kw.chatbot.messenger'].search([
            ('provider', '=', 'help_crunch')],
            limit=1).get_helpcrunch_channels()
        channel = self.env['kw.chatbot.helpcrunch.channels'].search([
            ('helpcrunch_channel_id', '=', message.get('applicationId'))])
        sender = self.sudo().search([
            ('hc_token', '=', messenger.api_token),
            ('help_crunch_id', '=', str(kwargs['sender'].get('chat_id')))],
            limit=1)
        if not sender:
            sender = self.sudo().create({
                'name': customer.get('name'),
                'help_crunch_channel_id': channel.id,
                'messenger_id': messenger.id,
                'hc_token': messenger.api_token,
                'help_crunch_id': str(kwargs['sender'].get('chat_id')),
                'help_crunch_username': customer.get('name'),
                'help_crunch_email': customer.get('email'),
                'help_crunch_userId': customer.get('userId'), })
        return sender

    def aprove_sender(self):
        for obj in self:
            if obj.provider == 'help_crunch':
                raise exceptions.UserError(_(
                    'This sender (HelpCrunch) cannot become an operator'))
        return super().aprove_sender()

    def reject_sender(self):
        for obj in self:
            if obj.provider == 'help_crunch':
                raise exceptions.UserError(_(
                    'This sender (HelpCrunch) cannot become an operator'))
        return super().aprove_sender()
