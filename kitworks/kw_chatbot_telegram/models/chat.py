import base64
import hashlib
import logging
import os
from urllib import request as urllib_request

from telebot import TeleBot
import requests
from odoo import models, fields, api, exceptions, _

_logger = logging.getLogger(__name__)


def load_image_from_url(url, headers=False):
    headers = headers or {}
    if 'User-Agent' not in headers:
        headers['User-Agent'] = 'Wget/1.11.4'
        # headers['User-Agent'] = \
        #     'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) ' \
        #     'AppleWebKit/537.36 (KHTML, like Gecko) ' \
        #     'Chrome/50.0.2661.102 Safari/537.36'
    req = urllib_request.Request(url.strip(), None, headers)
    # pylint: disable=E8106
    res = urllib_request.urlopen(req)
    return res.read()


class KwTeleBot(TeleBot):
    conversation = None
    sender = None
    chat = None


class Chat(models.Model):
    _inherit = 'kw.chatbot.chat'

    telegram_token = fields.Char()

    telegram_access_token = fields.Char()

    telegram_update_hook_response = fields.Text(
        readonly=True, )
    telegram_developer_url = fields.Char()

    telegram_location = fields.Char()
    first_name_bot = fields.Char()

    @api.constrains('telegram_token', 'messenger_id')
    def _constrain_telegram_token(self):
        for obj in self:
            if not obj.messenger_id:
                continue
            if obj.messenger_id.provider != 'telegram':
                continue
            if not obj.telegram_token:
                raise exceptions.ValidationError(_(
                    '"Telegram token" is required for Telegram chat'))

    def telegram_update_hook_address(self):
        self.ensure_one()
        access_token = self.telegram_generate_access_token()
        self.telegram_access_token = access_token
        burl = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        if self.is_developer_mode:
            burl = self.telegram_developer_url.strip()
        url = 'https://api.telegram.org/bot{}/setWebhook?url=' \
              '{}/kw_chatbot/telegram/bot/{}/{}' \
              ''.format(self.telegram_token, burl, self.id, access_token)
        # pylint: disable=E8106
        r = requests.get(url)
        self.telegram_get_name_bot()
        self.telegram_update_hook_response = r.text

    def telegram_get_name_bot(self):
        self.ensure_one()
        url = 'https://api.telegram.org/bot{}/getMe'.format(
            self.telegram_token)
        # pylint: disable=E8106
        response = requests.get(url)
        if 200 <= response.status_code < 300:
            r = response.json()
            self.write(
                {'first_name_bot': r['result']['first_name'],
                 'name': r['result']['first_name'], })

    @api.model
    def telegram_generate_access_token(self):
        r_bytes = os.urandom(16)
        return str(hashlib.sha256(r_bytes).hexdigest())

    # pylint: disable=too-many-statements
    def telegram_get_telegram_bot(self):
        self.ensure_one()
        bot = KwTeleBot(self.telegram_token, threaded=False)
        bot.chat = self

        def callback_button_name(call):
            data = call.data
            inline_keyboards = call.message.json.get('reply_markup').get(
                'inline_keyboard')
            if data and inline_keyboards:
                for i in inline_keyboards:
                    if i[0].get('callback_data') \
                            and i[0].get('callback_data') == data:
                        return i[0]['text']
            return None

        def callback_query_handler(call):
            # _logger.info('callback_query_handler')
            # _logger.info(call)
            message = call.message
            sender = self.env['kw.chatbot.sender'].sudo().get_or_create(
                messenger=self.messenger_id, from_user=call.from_user)
            bot.sender = sender
            # _logger.info(sender)
            conversation = self.env['kw.chatbot.conversation'].sudo(
            ).get_or_create(chat=self, message=message, sender=sender)
            bot.conversation = conversation
            bot.chat.log_id.write(
                {'sender_id': sender.id,
                 'conversation_id': conversation.id})
            conversation.last_activity_datetime = fields.Datetime.now()
            conversation.chatbot_message_id = \
                self.env['kw.chatbot.message'].sudo().create({
                    'telegram_id': message.message_id,
                    'conversation_id': conversation.id,
                    'sender_id': sender.id,
                    'is_call_back_message': True,
                    'text': callback_button_name(call),
                    'name': message.message_id, }).id
            conversation.telegram_get_response(bot, call)

        def message_handler(message):
            # _logger.info('message_handler')
            # _logger.info(message)
            sender = self.env['kw.chatbot.sender'].sudo().get_or_create(
                messenger=self.messenger_id, from_user=message.from_user)
            bot.sender = sender
            conversation = self.env['kw.chatbot.conversation'].sudo(
            ).get_or_create(chat=self, message=message, sender=sender)
            bot.conversation = conversation
            bot.chat.log_id.write(
                {'sender_id': sender.id,
                 'conversation_id': conversation.id})
            conversation.last_activity_datetime = fields.Datetime.now()
            # get reply message
            reply_message = message.json.get('reply_to_message')
            if reply_message:
                reply_message = self.env['kw.chatbot.message'].sudo().search(
                    [('name', '=', int(reply_message.get('message_id')))])
                if reply_message:
                    reply_message = reply_message[0]
            chatbot_message_id = self.env['kw.chatbot.message'].sudo().create({
                'telegram_id': message.message_id,
                'conversation_id': conversation.id,
                'sender_id': sender.id,
                'raw_json': str(message.json),
                'text': message.text if message.text else message.location,
                'name': str(message.message_id),
                'kw_parent_id': reply_message.id if reply_message else False,
            }).id
            conversation.chatbot_message_id = chatbot_message_id

            conversation.telegram_get_response(bot, message.json)

        def video_handler(message):
            # _logger.info('video_handler')
            # _logger.info(message)
            sender = self.env['kw.chatbot.sender'].sudo().get_or_create(
                messenger=self.messenger_id, from_user=message.from_user)
            bot.sender = sender
            conversation = self.env['kw.chatbot.conversation'].sudo(
            ).get_or_create(chat=self, message=message, sender=sender)
            bot.conversation = conversation
            bot.chat.log_id.write(
                {'sender_id': sender.id,
                 'conversation_id': conversation.id})
            conversation.last_activity_datetime = fields.Datetime.now()
            text = message.video.file_name if message.video else 'void'
            message_data = {
                'telegram_id': message.message_id,
                'conversation_id': conversation.id,
                'sender_id': sender.id,
                'text': text,
                'name': message.message_id, }
            if message.video:
                data = load_image_from_url(
                    bot.get_file_url(message.video.file_id))
                data = base64.b64encode(data)
                attachment = self.env['ir.attachment'].sudo().create({
                    'name': message.video.file_name, 'datas': data,
                    'mimetype': message.video.mime_type, })
                message_data.update({'attachment_ids': [(4, attachment.id)]})
            if message.video_note:
                data = load_image_from_url(
                    bot.get_file_url(message.video_note.file_id))
                data = base64.b64encode(data)
                attachment = self.env['ir.attachment'].sudo().create({
                    'name': 'void', 'datas': data,
                    'mimetype': 'video/mp4', })
                message_data.update({'attachment_ids': [(4, attachment.id)]})
            msg = self.env['kw.chatbot.message'].sudo().create(message_data)
            conversation.chatbot_message_id = msg.id
            conversation.telegram_get_response(bot, message.json)

        def audio_handler(message):
            # _logger.info('audio_handler')
            # _logger.info(message)
            sender = self.env['kw.chatbot.sender'].sudo().get_or_create(
                messenger=self.messenger_id, from_user=message.from_user)
            bot.sender = sender
            conversation = self.env['kw.chatbot.conversation'].sudo(
            ).get_or_create(chat=self, message=message, sender=sender)
            bot.conversation = conversation
            bot.chat.log_id.write(
                {'sender_id': sender.id,
                 'conversation_id': conversation.id})
            conversation.last_activity_datetime = fields.Datetime.now()
            message_data = {
                'telegram_id': message.message_id,
                'conversation_id': conversation.id,
                'sender_id': sender.id,
                'text': message.document or message.audio.file_name,
                'name': message.message_id, }
            if message.audio:
                data = load_image_from_url(
                    bot.get_file_url(message.audio.file_id))
                data = base64.b64encode(data)
                attachment = self.env['ir.attachment'].sudo().create({
                    'name': message.audio.file_name, 'datas': data,
                    'mimetype': message.audio.mime_type, })
                message_data.update({'attachment_ids': [(4, attachment.id)]})
            msg = self.env['kw.chatbot.message'].sudo().create(message_data)
            conversation.chatbot_message_id = msg.id
            conversation.telegram_get_response(bot, message.json)

        def document_handler(message):
            sender = self.env['kw.chatbot.sender'].sudo().get_or_create(
                messenger=self.messenger_id, from_user=message.from_user)
            bot.sender = sender
            conversation = self.env['kw.chatbot.conversation'].sudo(
            ).get_or_create(chat=self, message=message, sender=sender)
            bot.conversation = conversation
            bot.chat.log_id.write({
                'sender_id': sender.id,
                'conversation_id': conversation.id})
            conversation.last_activity_datetime = fields.Datetime.now()
            message_data = {
                'telegram_id': message.message_id,
                'conversation_id': conversation.id,
                'sender_id': sender.id,
                'text': message.document or message.photo or message.voice,
                'name': message.message_id, }
            if message.voice:
                data = load_image_from_url(
                    bot.get_file_url(message.voice.file_id))
                data = base64.b64encode(data)
                data = data.decode('utf-8')
                attachment = self.env['ir.attachment'].sudo().create({
                    'name': message.voice.file_size, 'datas': data,
                    'mimetype': message.voice.mime_type, })
                message_data.update({'attachment_ids': [(4, attachment.id)]})

            if message.document:
                data = load_image_from_url(
                    bot.get_file_url(message.document.file_id))
                data = base64.b64encode(data)
                data = data.decode('utf-8')
                attachment = self.env['ir.attachment'].sudo().create({
                    'name': message.document.file_name, 'datas': data,
                    'mimetype': message.document.mime_type, })
                message_data.update({'attachment_ids': [(4, attachment.id)]})
            elif message.photo:
                # _logger.info(message.photo.file_size)
                file = sorted(
                    [{'file_id': x.file_id, 'file_size': x.file_size}
                     for x in message.photo],
                    key=lambda d: d['file_size'], reverse=True, )
                file = bot.get_file(file[0]['file_id'])
                data = load_image_from_url(
                    bot.get_file_url(file.file_id))
                data = base64.b64encode(data)
                data = data.decode('utf-8')
                attachment = self.env['ir.attachment'].sudo().create({
                    'name': file.file_path.split('/')[-1], 'datas': data, })
                message_data.update({'attachment_ids': [(4, attachment.id)]})
            msg = self.env['kw.chatbot.message'].sudo().create(message_data)
            conversation.chatbot_message_id = msg.id
            conversation.telegram_get_response(bot, message.json)

        bot.message_handler(
            content_types=['document', 'photo', 'voice'])(document_handler)
        bot.message_handler(
            content_types=['text', 'location', 'contact'])(message_handler)
        bot.message_handler(
            content_types=['video', 'video_note'])(video_handler)
        bot.message_handler(
            content_types=['audio'])(audio_handler)
        bot.callback_query_handler(
            func=lambda x: True)(callback_query_handler)
        return bot
