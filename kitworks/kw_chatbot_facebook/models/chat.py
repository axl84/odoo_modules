import hashlib
import logging
import os

from pymessenger.bot import Bot
from odoo import models, fields, api
from odoo.addons.kw_graph_api.models.graph_api import FacebookGraphApi

_logger = logging.getLogger(__name__)


class KwFacebookBot(Bot):
    conversation = None
    sender = None
    chat = None


class Chat(models.Model):
    _inherit = 'kw.chatbot.chat'

    facebook_timestamp = fields.Float()

    facebook_access_token = fields.Char()

    facebook_developer_url = fields.Char()

    facebook_verify_token = fields.Char()

    facebook_copy_url = fields.Char()

    facebook_webhook_token = fields.Char()

    facebook_account_id = fields.Char()
    is_facebook_login = fields.Boolean(
        default=False, )
    is_facebook_developer_mode = fields.Boolean(
        default=False, )
    facebook_app_id = fields.Char()
    facebook_app_secret = fields.Char()

    def get_facebook_long_lived_token(self):
        params = {
            'grant_type': 'fb_exchange_token',
            'client_id': self.facebook_app_id,
            'client_secret': self.facebook_app_secret,
            'fb_exchange_token': self.facebook_access_token}
        res = FacebookGraphApi().get_facebook_graph(
            url='/oauth/access_token', params=params)
        if res.get('data'):
            token = res['data'].get('access_token')
            if token:
                self.write({'facebook_access_token': token})
        else:
            raise ValueError('Failed to get long-term token!{}'.format(
                res.get('error')))

    def facebook_subscribed_fields(self):
        body = {
            'subscribed_fields': ['messages'],
            'access_token': self.facebook_access_token, }
        res = FacebookGraphApi().post_facebook_graph(
            url='/v14.0/{}/subscribed_apps'.format(
                self.facebook_account_id), body=body)
        if res.get('error'):
            raise ValueError(res.get('error'))

    @api.onchange('facebook_webhook_token')
    def onchange_attribute_id(self):
        for obj in self:
            burl = self.env['ir.config_parameter'].sudo().get_param(
                'web.base.url')
            if obj.facebook_webhook_token:
                url = '{}/kw_chatbot/facebook/bot/{}'.format(
                    burl, obj.facebook_webhook_token)
                obj.write({
                    'facebook_copy_url': url, })

    def facebook_copy_url_button(self):
        burl = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        webhook_token = self.facebook_generate_verify_token()
        self.write({
            'facebook_webhook_token': webhook_token,
            'facebook_copy_url': '{}/kw_chatbot/facebook/bot/{}'.format(
                burl, webhook_token), })

    def set_facebook_verify_token(self):
        for obj in self:
            obj.facebook_verify_token = obj.facebook_generate_verify_token()

    @api.model
    def facebook_generate_verify_token(self):
        r_bytes = os.urandom(16)
        return str(hashlib.sha256(r_bytes).hexdigest())

    def facebook_get_facebook_bot(self):
        self.ensure_one()
        bot = KwFacebookBot(self.facebook_access_token)
        bot.chat = self
        return bot

    def get_facebook_sender_name(self, **kwargs):
        sender_id = kwargs.get('sender')
        if not sender_id:
            raise ValueError('Cant process message: "sender" not provided')
        params = {
            'access_token': self.facebook_access_token}
        res = FacebookGraphApi().get_facebook_graph(
            url='/{}'.format(sender_id), params=params)
        if res.get('data'):
            return res.get('data')
        return sender_id

    def facebook_process_message(self, message, log):
        self.ensure_one()
        # _logger.info('facebook_process_message')
        bot = self.facebook_get_facebook_bot()
        sender_inf = self.get_facebook_sender_name(
            sender=message['sender']['id'])
        sender = self.env['kw.chatbot.sender'].sudo().get_or_create(
            messenger=self.messenger_id, sender=sender_inf)
        bot.sender = sender
        conversation = self.env['kw.chatbot.conversation'].sudo(
        ).get_or_create(chat=self, message=message, sender=sender)
        bot.conversation = conversation
        log.sudo().write(
            {'sender_id': sender.id,
             'conversation_id': conversation.id})
        msg = message.get('message') if message.get('message') else message
        text = msg.get('postback') if msg.get('postback') else msg.get('text')
        if not isinstance(text, str):
            text = text.get('payload') if text.get('payload') else text
        conversation.chatbot_message_id = \
            self.env['kw.chatbot.message'].sudo().create({
                'facebook_id': sender.id,
                'conversation_id': conversation.id,
                'sender_id': sender.id, 'text': text,
                'name': text, })
        conversation.last_activity_datetime = fields.Datetime.now()
        conversation.facebook_get_response(bot, message)

    def facebook_callback_handler(self, message, log):
        self.ensure_one()
        # _logger.info('facebook_callback_handler')
        bot = self.facebook_get_facebook_bot()
        sender = self.env['kw.chatbot.sender'].sudo().get_or_create(
            messenger=self.messenger_id, sender=message['sender']['id'])
        bot.sender = sender
        conversation = self.env['kw.chatbot.conversation'].sudo(
        ).get_or_create(chat=self, message=message, sender=sender)
        bot.conversation = conversation
        log.sudo().write(
            {'sender_id': sender.id,
             'conversation_id': conversation.id})
        msg = message.get('message') if message.get('message') else message
        text = msg.get('postback') if msg.get('postback') else msg.get('text')
        if not isinstance(text, str):
            text = text.get('payload') if text.get('payload') else text
        conversation.chatbot_message_id = \
            self.env['kw.chatbot.message'].sudo().create({
                'facebook_id': sender.id,
                'is_call_back_message': True,
                'conversation_id': conversation.id,
                'sender_id': sender.id,
                'text': message.get('postback').get('title'),
                'name': text, })
        conversation.last_activity_datetime = fields.Datetime.now()
        conversation.facebook_get_response(bot, message)

    def facebook_process_call(self, jsonrequest, log):
        self.ensure_one()
        # _logger.info('facebook_process_call')
        for event in jsonrequest.get('entry'):
            messaging = event['messaging']
            for message in messaging:
                if self.facebook_timestamp == float(message.get('timestamp')):
                    # _logger.info('facebook_timestamp duplicate message')
                    return "success"
                if message.get('message'):
                    self.facebook_timestamp = message.get('timestamp')
                    self.facebook_process_message(message, log)
                elif message.get('postback'):
                    self.facebook_timestamp = message.get('timestamp')
                    self.facebook_callback_handler(message, log)
                elif message.get('referral'):
                    self.facebook_timestamp = message.get('timestamp')
                    self.facebook_process_referral(message, log)
        return None

    def facebook_process_referral(self, message, log):
        self.ensure_one()
        # _logger.info('facebook_process_referral')

        def check_context(context):
            try:
                index = int(context)
            except Exception as e:
                _logger.debug(e)
                index = False
            return index

        bot = self.facebook_get_facebook_bot()
        sender = self.env['kw.chatbot.sender'].sudo().get_or_create(
            messenger=self.messenger_id, sender=message['sender']['id'])
        bot.sender = sender
        conversation = self.env['kw.chatbot.conversation'].sudo(
        ).get_or_create(chat=self, message=message, sender=sender)
        bot.conversation = conversation
        log.sudo().write(
            {'sender_id': sender.id,
             'conversation_id': conversation.id})
        text = message['referral']['ref'] if message.get('referral') else False
        conversation.chatbot_message_id = \
            self.env['kw.chatbot.message'].sudo().create({
                'facebook_id': sender.id,
                'conversation_id': conversation.id,
                'sender_id': sender.id, 'text': text,
                'name': text, })
        conversation.last_activity_datetime = fields.Datetime.now()
        if check_context(text):
            conversation.facebook_utm_data(int(text))
            markup = [{"type": "postback",
                       "title": 'Start',
                       "payload": '/start'}]
            conversation.send_message(
                text='Hello!', markup=markup)
