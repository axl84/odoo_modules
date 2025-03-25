import logging

import requests
from odoo import fields, models, api, _

_logger = logging.getLogger(__name__)


class ConversationWizard(models.TransientModel):
    _name = 'kw.conversation.wizard.umnico'
    _description = 'Conversation Wizard'

    messenger_id = fields.Many2one(
        comodel_name='kw.chatbot.messenger', readonly=True)
    partner_id = fields.Many2one(
        comodel_name='res.partner', required=True)
    mobile = fields.Char(related='partner_id.mobile')
    umnico_channel_id = fields.Many2one(
        comodel_name='kw.chatbot.umnico.channels', required=True,
        domain=['|', ('type', '=', 'whatsapp2'), ('type', '=', 'telegram')])
    text_message = fields.Text(required=True)

    @api.model
    def default_get(self, vals):
        res = super(ConversationWizard, self).default_get(vals)
        messenger_id = self.env['kw.chatbot.messenger'].sudo().search([
            ('provider', '=', 'umnico')], limit=1)
        res['messenger_id'] = messenger_id.id
        return res

    def add_conversation(self):
        self.ensure_one()
        try:
            body = {
                "message": {
                    "text": self.text_message,
                },
                "destination": self.mobile,
                "saId": int(self.umnico_channel_id.umnico_channel_id)
            }
            # pylint: disable=E8106
            response = requests.request(
                method='post',
                url='https://api.umnico.com/v1.3/messaging/post',
                headers={'Authorization': 'Bearer {}'.format(
                    self.messenger_id.umnico_api_token),
                    'Host': 'api.umnico.com'},
                json=body, )
            if 200 <= response.status_code < 300:
                contact = response.json()
                if contact:
                    data = {
                        'name': self.partner_id.name,
                        'umnico_channel_id': self.umnico_channel_id.id,
                        'messenger_id': self.messenger_id.id,
                        'umnico_saId': contact[0].get('sa').get('id'),
                        'partner_id': self.partner_id.id,
                        'login': self.partner_id.mobile,

                    }
                    sender = self.create_sender(data)
                    sender.is_person = True
                    conv = self.env['kw.chatbot.conversation'].sudo(
                    ).get_or_create(
                        chat=self.messenger_id.chatbot_chat_ids[0],
                        sender=sender, )
                    conv.write({'is_personal': True})
                    subtype = self.env['mail.message.subtype'].search(
                        [('default', '=', True)], limit=1)

                    conv.mail_channel_id.message_post(
                        author_id=conv.sender_id.partner_id.id,
                        body=_(''),
                        message_type='comment',
                        subtype_id=subtype.id, )
                    conv.mail_channel_id.message_post(
                        author_id=self.env.user.partner_id.id,
                        body=_(self.text_message),
                        message_type='comment',
                        subtype_id=subtype.id, )
                    conv.umnico_create_log(name='OUT', body=body)
                    conv.connect_live_chat(text=self.text_message)
                    conv.livechat_open_and_subscribe_button()
                    conv.umnico_out_message(text=self.text_message)

        except Exception as e:
            _logger.debug(e)

    def create_sender(self, data):
        self.ensure_one()
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
