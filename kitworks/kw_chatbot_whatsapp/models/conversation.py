import logging

from odoo.addons.kw_graph_api.models.graph_api import FacebookGraphApi
from odoo import models, fields, exceptions, api, _

_logger = logging.getLogger(__name__)


class Conversation(models.Model):
    _inherit = 'kw.chatbot.conversation'

    whatsapp_id = fields.Char()

    is_whatsapp_send = fields.Boolean()

    def get_or_create_partner(self, sender_id, company_id=False):
        res = super().get_or_create_partner(sender_id, company_id)
        if sender_id.messenger_id.provider != 'whatsapp':
            return res
        res.write({'phone': sender_id.whatsapp_id})
        return res

    @api.model
    def get_or_create(self, chat, **kwargs):
        if chat.messenger_id.provider != 'whatsapp':
            return super().get_or_create(chat, **kwargs)
        contact = kwargs.get('contact')
        sender = kwargs.get('sender')
        conversation = self.sudo().search([
            ('whatsapp_id', '=', contact.get('wa_id')),
            ('company_id', '=', chat.company_id.id),
            ('chat_id', '=', chat.id)], limit=1)
        if conversation:
            if conversation.dialog_id.is_partner:
                self.get_or_create_partner(
                    sender_id=conversation.sender_id,
                    company_id=chat.company_id)
        if not conversation:
            conversation = self.sudo().create({
                'name': contact.get('wa_id'), 'dialog_id': chat.dialog_id.id,
                'sender_id': sender.id, 'chat_id': chat.id,
                'company_id': chat.company_id.id,
                'whatsapp_id': contact.get('wa_id'), })
            if conversation.dialog_id.is_partner:
                self.get_or_create_partner(
                    sender_id=conversation.sender_id,
                    company_id=chat.company_id)
                conversation.create_live_chat_channel(
                    conversation.sender_id.partner_id)
        return conversation

    def whatsapp_get_response(self, message):
        self.is_whatsapp_send = False
        if self.dialog_id.bots_type == 'is_consultant_bot':
            if not self.sender_id.aproved_consultant and \
                    not self.sender_id.is_chatbot_consultant:
                self.send_message(
                    text='Ask an administrator to make you a consultant')
                self.write({'is_whatsapp_send': True})
                return
            if message in ['/start', '/end']:
                if message == '/start':
                    self.sender_id.is_ready_for_consult = True
                    self.send_message(text='You OnLine')
                if message == '/end':
                    self.sender_id.is_ready_for_consult = False
                    self.send_message(text='You OffLine')
            self.write({'is_whatsapp_send': True})
        if self.is_whatsapp_send:
            return
        if not self.is_whatsapp_send:
            self.whatsapp_does_not_found()

    def whatsapp_does_not_found(self):
        self.ensure_one()
        lang = self.sender_id.partner_id.lang
        alternative = _('There is no answer for your request')
        text = self.dialog_id.with_context(
            lang=lang).not_found_msg.strip() or alternative
        self.send_message(text=text)

    def get_whatsapp_button(self, text, button_vals):
        vals = []
        for button in button_vals:
            if not button.get('id') or not button.get('title'):
                raise exceptions.ValidationError(
                    _('The fields are "id" and "title" '
                      'are required in the button'))
            button = {
                "type": "reply",
                "reply": {
                    "id": button.get('id'),
                    "title": button.get('title')}}
            vals.append(button)
        return {
            'messaging_product': 'whatsapp',
            'to': self.sender_id.whatsapp_id,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": text},
                "action": {
                    "buttons": vals}}}

    def send_message(self, text, **kwargs):
        self.ensure_one()
        if self.chat_id.messenger_id.provider != 'whatsapp':
            return super().send_message(text, **kwargs)
        button = kwargs.get('button')
        try:
            headers = {
                'Authorization': 'Bearer {}'.format(
                    self.chat_id.whatsapp_access_token),
                'Content-Type': 'application/json'}
            params = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": self.sender_id.whatsapp_id,
                "type": "text",
                "text": {
                    "body": text}}
            if button:
                params = self.get_whatsapp_button(
                    text=text, button_vals=button)
            res = FacebookGraphApi().post_facebook_graph(
                url='/{}/messages'.format(
                    self.chat_id.whatsapp_phone_number_id),
                body=params, headers=headers)
            data = {'text': text}
            self.is_whatsapp_send = True
            self.whatsapp_out_message(text=data)
            self.whatsapp_create_log(name='OUT', body=res)
            return data
        except Exception as e:
            _logger.info(e)
        return False

    def whatsapp_out_message(self, text=False):
        if not text:
            text = False
        name = text.get('name') if text.get('name') else False
        text = text.get('text') if text.get('text') else False
        sender = self.env['kw.chatbot.sender'].search([
            ('name', '=', 'WhatsAppBot')], limit=1)
        self.env['kw.chatbot.message'].sudo().create({
            'conversation_id': self.id, 'is_bot_message': True,
            'sender_id': sender.id, 'text': text,
            'name': name if name else 'Whatsapp', })

    def whatsapp_create_log(self, name=False, body=False):
        self.ensure_one()
        self.env['kw.chatbot.log'].create({
            'name': name,
            'messenger_id':  self.chat_id.messenger_id.id,
            'body': body,
            'chat_id': self.chat_id.id,
            'dialog_id': self.dialog_id.id,
            'sender_id': self.sender_id.id,
            'conversation_id': self.id, })

    def send_whatsapp_template(self, template):
        try:
            headers = {
                'Authorization': 'Bearer {}'.format(
                    self.chat_id.whatsapp_access_token),
                'Content-Type': 'application/json'}
            params = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": self.sender_id.whatsapp_id,
                "type": "template",
                "template": {
                    'name': template.template_name,
                    'language': {'code': template.lang}}}
            FacebookGraphApi().post_facebook_graph(
                url='/{}/messages'.format(
                    self.chat_id.whatsapp_phone_number_id),
                body=params, headers=headers)
        except Exception as e:
            _logger.info(e)


class Message(models.Model):
    _inherit = 'kw.chatbot.message'

    whatsapp_id = fields.Char(store=True, readonly=True)
