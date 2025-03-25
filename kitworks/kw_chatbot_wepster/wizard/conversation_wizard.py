import logging

import requests
from odoo import fields, models, api, _

_logger = logging.getLogger(__name__)


class ConversationWizard(models.TransientModel):
    _name = 'kw.conversation.wizard'
    _description = 'Conversation Wizard'

    messenger_id = fields.Many2one(
        comodel_name='kw.chatbot.messenger', readonly=True)
    partner_id = fields.Many2one(
        comodel_name='res.partner', required=True)
    mobile = fields.Char(related='partner_id.mobile')
    webster_channel_id = fields.Many2one(
        comodel_name='kw.chatbot.wepster.channels', required=True)

    @api.model
    def default_get(self, vals):
        res = super(ConversationWizard, self).default_get(vals)
        messenger_id = self.env['kw.chatbot.messenger'].sudo().search([
            ('provider', '=', 'wepster')], limit=1)
        res['messenger_id'] = messenger_id.id
        return res

    def add_conversation(self):
        self.ensure_one()
        try:
            body = {
                "connectionId": self.webster_channel_id.wepster_channel_id,
                "channelType": self.webster_channel_id.type,
                "name": self.partner_id.name,
                "phone": self.partner_id.mobile, }
            # pylint: disable=E8106
            response = requests.request(
                method='post',
                url='https://my.wepster.com/api/v1/contact/add',
                headers={'wepster': self.messenger_id.wepster_api_token},
                json=body,)
            if 200 <= response.status_code < 300:
                contact = response.json()
                if contact:
                    data = {
                        'name': self.partner_id.name,
                        'wepster_channel_id': self.webster_channel_id.id,
                        'messenger_id': self.messenger_id.id,
                        'wepster_id': contact.get('wepster_id'),
                        'wepster_username': self.partner_id.name,
                        'partner_id': self.partner_id.id,
                        'wepster_userId': contact.get('wepster_id'), }
                    sender = self.create_sender(data)
                    conv = self.env['kw.chatbot.conversation'].sudo(
                    ).get_or_create(
                        chat=self.messenger_id.chatbot_chat_ids[0],
                        sender=sender, )
                    conv.connect_live_chat(text='')
                    conv.livechat_open_and_subscribe_button()
        except Exception as e:
            _logger.debug(e)

    def create_sender(self, data):
        self.ensure_one()
        sender = self.env['kw.chatbot.sender'].sudo().search([
            ('wepster_id', '=', data.get('wepster_id'))], limit=1)
        if not sender:
            sender = self.env['kw.chatbot.sender'].sudo().create(data)
        return sender

    def conversation_action_button(self):
        return {
            'name': _('Chatbot Conversation'),
            'view_mode': 'tree,form',
            'res_model': 'kw.chatbot.conversation',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('partner_id', '=', self.partner_id.id)],
            'context': {
                'default_partner_id': self.partner_id.id,
                'search_partner_id': self.partner_id.id}}
