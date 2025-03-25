import logging

from odoo import models, fields, api, exceptions, _

_logger = logging.getLogger(__name__)


class Sender(models.Model):
    _inherit = 'kw.chatbot.sender'

    umnico_id = fields.Char()
    umnico_accountId = fields.Char()
    umnico_leadId = fields.Char()
    umnico_realId = fields.Char()
    umnico_customerId = fields.Char()
    umnico_username = fields.Char()
    umnico_socialId = fields.Char()
    umnico_profileUrl = fields.Char()
    umnico_channel_id = fields.Many2one(
        comodel_name='kw.chatbot.umnico.channels', readonly=True, )
    is_person = fields.Boolean(default=True)
    umnico_saId = fields.Char()
    login = fields.Char()

    @api.model
    def get_or_create(self, messenger, **kwargs):
        if messenger.provider != 'umnico':
            return super().get_or_create(messenger, **kwargs)
        data = kwargs['sender']
        accountId = data.get('accountId')
        leadId = data.get('leadId')
        message = data.get('message')
        source = message.get('source')
        channel = message.get('sa')
        sender = message.get('sender')
        self.env['kw.chatbot.messenger'].search([
            ('provider', '=', 'umnico')],
            limit=1).get_umnico_channels()
        channel = self.env['kw.chatbot.umnico.channels'].search([
            ('umnico_channel_id', '=', channel.get('id'))])
        sender_id = self.sudo().search([
            ('login', '=', sender.get('login'))], limit=1)

        if not sender_id:
            sender_id = self.sudo().create({
                'name': sender.get('login'),
                'umnico_channel_id': channel.id if channel else False,
                'messenger_id': messenger.id,
                'umnico_id': sender.get('id'),
                'umnico_username': sender.get('login'),
                'umnico_customerId': sender.get('customerId'),
                'umnico_socialId': sender.get('socialId'),
                'umnico_profileUrl': sender.get('profileUrl'),
                'umnico_accountId': accountId,
                'umnico_leadId': leadId,
                'umnico_realId': source.get('realId'),
                'umnico_saId': source.get('saId', False),
                'is_person': False,
                'login': sender.get('login'), })
        if channel.type in ['whatsapp2', 'telegram']:
            if sender_id.partner_id:
                sender_id.partner_id.mobile = sender.get('login')
            sender_id.is_person = True
        return sender_id

    def aprove_sender(self):
        for obj in self:
            if obj.provider == 'umnico':
                raise exceptions.UserError(_(
                    'This sender (Umnico) cannot become an operator'))
        return super().aprove_sender()

    def reject_sender(self):
        for obj in self:
            if obj.provider == 'umnico':
                raise exceptions.UserError(_(
                    'This sender (Umnico) cannot become an operator'))
        return super().aprove_sender()
