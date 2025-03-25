import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class Conversation(models.Model):
    _inherit = 'kw.chatbot.conversation'

    instagram_id = fields.Integer()

    is_instagram_send = fields.Boolean()

    def send_message(self, text, **kwargs):
        self.ensure_one()
        if self.chat_id.messenger_id.provider != 'instagram':
            return super().send_message(text, **kwargs)
        _logger.info('_____Send_message_____')
        bot = self.chat_id.instagram_get_instagram_bot()
        markup = kwargs.get('markup')
        self.is_instagram_send = True
        if not self.wired_conversation_id:
            data = {'text': text}
            if markup:
                data['buttons'] = [i['title'] for i in markup]
            self.instagram_out_message(text=data)
        if markup:
            while markup:
                m = markup[:3]
                markup = markup[3:]
                res = bot.send_button_message(
                    self.sender_id.instagram_id, text, m)
                _logger.info('_____Instagram OUT_____')
                _logger.info(res)
                self.instagram_create_log(name='OUT', body=res)
        else:
            res = bot.send_text_message(
                self.sender_id.instagram_id, text)
            _logger.info('_____Instagram OUT_____')
            _logger.info(res)
            self.instagram_create_log(name='OUT', body=res)
        return None

    # pylint: disable=R1711
    def instagram_out_message(self, text=False):
        self.ensure_one()
        if not self.wired_conversation_id and not self.operator_live_id:
            sender = self.env['kw.chatbot.sender'].search([
                ('name', '=', 'InstagramBot')], limit=1)
            self.env['kw.chatbot.message'].sudo().create({
                'conversation_id': self.id, 'is_bot_message': True,
                'sender_id': sender[0].id, 'text': text,
                'name': 'None', })
        return None

    def instagram_create_log(self, name=False, body=False):
        self.ensure_one()
        self.env['kw.chatbot.log'].create({
            'name': name,
            'messenger_id':  self.chat_id.messenger_id.id,
            'body': body,
            'chat_id': self.chat_id.id,
            'dialog_id': self.dialog_id.id,
            'sender_id': self.sender_id.id,
            'conversation_id': self.id,
        })

    def instagram_get_message_data(self, message):
        msg = message.get('message') if message.get('message') else message
        text = msg.get('postback') if msg.get('postback') else msg.get('text')
        if not isinstance(text, str):
            text = text.get('payload') if text.get('payload') else text
        return text

    @api.model
    def get_or_create(self, chat, **kwargs):
        if chat.messenger_id.provider != 'instagram':
            return super().get_or_create(chat, **kwargs)
        sender = kwargs.get('sender')
        if not sender:
            raise ValueError('Cant process: "sender_id" not provided')
        conversation = self.sudo().search([
            ('sender_id', '=', sender.id),
            ('company_id', '=', chat.company_id.id),
            ('chat_id', '=', chat.id)], limit=1)
        # _logger.info(conversation)
        if not conversation:
            conversation = self.sudo().create({
                'name': sender.instagram_id,
                'dialog_id': chat.dialog_id.id,
                'sender_id': sender.id,
                'company_id': chat.company_id.id,
                'chat_id': chat.id, })

            if conversation.dialog_id.is_partner:
                self.get_or_create_partner(
                    sender_id=conversation.sender_id,
                    company_id=chat.company_id)
                conversation.create_live_chat_channel(
                    conversation.sender_id.partner_id)

        return conversation

    # pylint: disable=R1711
    def instagram_get_response(self, bot, message):
        self.ensure_one()
        if self.dialog_id.bots_type == 'is_consultant_bot':

            _logger.info("________________________________________")
            _logger.info(message)
            _logger.info("________________________________________")

            if not self.sender_id.aproved_consultant and \
                    not self.sender_id.is_chatbot_consultant:
                self.send_message(
                    text='Ask an administrator to make you a consultant')
                self.write({'is_instagram_send': True})
                return
            message = self.instagram_get_message_data(message)
            if message in ['/start', '/end']:
                if message == '/start':
                    self.sender_id.is_ready_for_consult = True
                    self.send_message(text='You OnLine')
                if message == '/end':
                    self.sender_id.is_ready_for_consult = False
                    self.send_message(text='You OffLine')
            self.write({'is_instagram_send': True})
        if self.is_instagram_send:
            return
        if not self.is_instagram_send:
            self.instagram_does_not_found()

    def instagram_does_not_found(self):
        self.ensure_one()
        self.send_message(text=self.dialog_id.not_found_msg.strip())

    def instagram_utm_data(self, index):
        self.ensure_one()
        if index:
            link_tracker = self.env['link.tracker'].search([
                ('id', '=', index)])
            if link_tracker:
                self.sudo().lint_tracker_id = link_tracker


class Message(models.Model):
    _inherit = 'kw.chatbot.message'

    instagram_id = fields.Char()

    raw_json = fields.Text()
