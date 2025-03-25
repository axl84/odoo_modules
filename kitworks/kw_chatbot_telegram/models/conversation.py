import base64
import logging
import tempfile
import io

from telebot import types
from odoo import models, fields, api, exceptions, _

_logger = logging.getLogger(__name__)


class Conversation(models.Model):
    _inherit = 'kw.chatbot.conversation'

    telegram_id = fields.Char()

    is_telegram_send = fields.Boolean()
    location_latitude = fields.Char()
    location_longitude = fields.Char()

    def send_message(self, text, **kwargs):
        self.ensure_one()
        if self.chat_id.messenger_id.provider != 'telegram':
            return super().send_message(text, **kwargs)
        bot = self.chat_id.telegram_get_telegram_bot()
        markup = kwargs.get('reply_markup') \
            if kwargs.get('reply_markup') else None
        reply_to_message_id = None
        if kwargs.get('kw_parent_id'):
            try:
                reply_to_message_id = int(kwargs.get('kw_parent_id'))
                # search message in kw.chatbot.message
                # by reply_to_message_id - 1
                telegram_message = self.env['kw.chatbot.message'].search([
                    ('id', '=', reply_to_message_id)], limit=1)
                if telegram_message.telegram_id > 0:
                    reply_to_message_id = telegram_message.telegram_id
                else:
                    telegram_message = self.env['kw.chatbot.message'].search([
                        ('id', '=', reply_to_message_id - 1)], limit=1)
                if telegram_message:
                    reply_to_message_id = telegram_message.telegram_id
            except ValueError:
                _logger.error('Telegram: reply_to_message_id is not int')
        try:
            res = bot.send_message(
                chat_id=self.telegram_id, text=text, reply_markup=markup,
                disable_web_page_preview=True,
                parse_mode='HTML', reply_to_message_id=reply_to_message_id)
            self.is_telegram_send = True
            data = {'text': text,
                    'name': str(res.id),
                    'telegram_id': str(res.id),
                    'raw_json': res.json, }
            if kwargs.get('buttons'):
                data['buttons'] = kwargs.get('buttons')
            self.telegram_out_message(text=data)
            self.telegram_create_log(name='OUT', body=res)
            return data
        except Exception as e:
            _logger.info(e)
        return False

    def get_attachment_url(self, attachment):
        burl = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        image_url = '{}/web/image/ir.attachment/{}/datas'.format(
            burl, attachment.id)
        if attachment.mimetype == 'image/jpeg':
            image_url += '?unique={}'.format(attachment.checksum)
        elif attachment.mimetype == 'image/png':
            image_url += '?unique={}'.format(attachment.checksum)
        else:
            image_url = False
        if not image_url:
            return False
        return image_url

    def telegram_send_file(self, file, filename=None):
        bot = self.chat_id.telegram_get_telegram_bot()
        if filename:
            file_object = io.BytesIO(file)
            file_object.name = filename
        else:
            file_object = file
        try:
            bot.send_document(
                self.telegram_id, document=file_object)
        except Exception as e:
            _logger.debug(e)

    def send_file(self, files, **kwargs):
        self.ensure_one()
        if self.chat_id.messenger_id.provider != 'telegram':
            return super().send_file(files, **kwargs)
        for file in files:
            media_murkup, media = [], []
            bot = self.chat_id.telegram_get_telegram_bot()
            if file.mimetype in ['image/jpeg', 'image/png']:
                caption = kwargs.get('text') if kwargs.get('text') else ''
                reply_markup = kwargs.get('reply_markup') \
                    if kwargs.get('reply_markup') else None

                bot.send_photo(
                    self.telegram_id, base64.b64decode(file.datas),
                    caption=caption, reply_markup=reply_markup)
            # elif file and file.datas:
            #     file = file.sudo()
            #     file_data = base64.b64decode(file.datas)
            #     with open(file.name, 'wb') as f:
            #         f.write(file_data)
            #     bot.send_document(
            #         self.telegram_id, document=open(file.name, 'rb'))
            elif file and file.datas:
                file_data = base64.b64decode(file.datas)
                if not file_data:
                    raise exceptions.ValidationError(
                        _('An error occurred while processing the file'))
                try:
                    media_file = tempfile.NamedTemporaryFile(
                        prefix=f"{'.'.join(file.name.split('.')[:-1])}{' ('}",
                        suffix=').{}'.format(file.name.split('.')[-1]))
                    media_file.write(file_data)
                    media_murkup.append(types.InputMediaDocument(
                        open(media_file.name, 'rb')))
                    if media_murkup:
                        bot.send_media_group(self.telegram_id, media_murkup)
                except Exception as e:
                    _logger.debug(e)
                    try:
                        media_murkup.clear()
                        media_murkup.append(types.InputMediaDocument(
                            io.BytesIO(file_data), caption=file.name))
                        if media_murkup:
                            bot.send_media_group(
                                self.telegram_id, media_murkup)
                    except Exception as g:
                        _logger.debug(g)
            if kwargs.get('not_create_log'):
                _logger.info('Telegram: not create log')
            else:
                self.telegram_out_message(text={'media': media})
        return None

    def telegram_out_message(self, text=False):
        if not text:
            text = False
        name = text.get('name') if text.get('name') else False
        text = text.get('text') if text.get('text') else False
        sender = self.env['kw.chatbot.sender'].search([
            ('name', '=', 'TelegramBot')], limit=1)
        self.env['kw.chatbot.message'].sudo().create({
            'conversation_id': self.id, 'is_bot_message': True,
            'sender_id': sender[0].id, 'text': text, 'name': name, })

    def telegram_create_log(self, name=False, body=False):
        self.ensure_one()
        self.env['kw.chatbot.log'].create({
            'name': name, 'messenger_id': self.chat_id.messenger_id.id,
            'body': body.json if body else '',
            'chat_id': self.chat_id.id, 'dialog_id': self.dialog_id.id,
            'sender_id': self.sender_id.id, 'conversation_id': self.id, })

    @api.model
    def get_or_create(self, chat, **kwargs):
        if chat.messenger_id.provider != 'telegram':
            return super().get_or_create(chat, **kwargs)
        message = kwargs.get('message')
        sender = kwargs.get('sender')
        if not message:
            raise ValueError(_('Cant process: "message" not provided'))
        conversation = self.sudo().search([
            ('telegram_id', '=', message.chat.id),
            ('company_id', '=', chat.company_id.id),
            ('chat_id', '=', chat.id)], limit=1)
        if conversation:
            if conversation.dialog_id.is_partner:
                conversation.get_or_create_partner(
                    sender_id=conversation.sender_id,
                    company_id=chat.company_id)
        if not conversation:
            conversation = self.sudo().create({
                'name': message.chat.id, 'dialog_id': chat.dialog_id.id,
                'sender_id': sender.id, 'chat_id': chat.id,
                'company_id': chat.company_id.id,
                'telegram_id': message.chat.id, })

            if conversation.dialog_id.is_partner:
                conversation.get_or_create_partner(
                    sender_id=conversation.sender_id,
                    company_id=chat.company_id)
                conversation.create_live_chat_channel(
                    conversation.sender_id.partner_id)

        return conversation

    def telegram_get_message_data(self, message):
        self.ensure_one()
        if isinstance(message, str):
            return message
        if hasattr(message, 'json'):
            msg = message.json
            text = msg.get('text') if msg.get('text') else msg.get('data')
        elif isinstance(message, dict):
            text = message.get('text') if message.get('text') \
                else message.get('data')
        else:
            text = message.text if hasattr(message, 'text') \
                else message.data
        if not text and message.get('location'):
            return message.get('location')
        if not text and message.get('contact'):
            return message.get('contact')
        if not text and message.get('caption'):
            return message.get('caption')
        return text

    def telegram_pre_response(self, bot, message):
        self.ensure_one()

    def telegram_get_response(self, bot, message):
        self.ensure_one()
        text = self.telegram_get_message_data(message)
        if isinstance(text, dict) and text.get('latitude'):
            self.write({
                'location_latitude': text.get('latitude'),
                'location_longitude': text.get('longitude'),
                'is_telegram_send': True})
        if self.dialog_id.bots_type == 'is_consultant_bot':
            if not self.sender_id.aproved_consultant and \
                    not self.sender_id.is_chatbot_consultant:
                self.send_message(
                    text='Ask an administrator to make you a consultant')
                self.write({'is_telegram_send': True})
                return
            text = self.telegram_get_message_data(message)
            if text in ['/start', '/end']:
                if text == '/start':
                    self.sender_id.is_ready_for_consult = True
                    self.send_message(text='You OnLine')
                if text == '/end':
                    self.sender_id.is_ready_for_consult = False
                    self.send_message(text='You OffLine')
            self.write({'is_telegram_send': True})
        self.telegram_pre_response(bot=bot, message=message)
        if self.is_telegram_send:
            return
        if not self.is_telegram_send:
            self.telegram_does_not_found()

    def telegram_does_not_found(self):
        self.ensure_one()
        lang = self.sender_id.partner_id.lang
        alternative = _('There is no answer for your request')
        text = self.dialog_id.with_context(
            lang=lang).not_found_msg.strip() or alternative
        self.send_message(
            text=text)


class Message(models.Model):
    _inherit = 'kw.chatbot.message'

    telegram_id = fields.Integer(
        store=True, readonly=True)

    raw_json = fields.Text()
