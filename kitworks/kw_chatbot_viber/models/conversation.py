import logging
import ast
import re
import json
from viberbot.api.messages.text_message import TextMessage
from viberbot.api.messages.file_message import FileMessage
from viberbot.api.messages.rich_media_message import RichMediaMessage
from viberbot.api.messages.keyboard_message import KeyboardMessage
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class Conversation(models.Model):
    _inherit = 'kw.chatbot.conversation'

    viber_id = fields.Char()

    is_viber_send = fields.Boolean()

    @staticmethod
    def viber_str_to_dict(input_str):
        try:
            input_str = input_str.replace('\'', '"')
            input_str = input_str.replace("'", '"')
            result_dict = json.loads(input_str)
            return result_dict
        except Exception as e:
            _logger.debug(e)
            return False

    @staticmethod
    def viber_get_message(message):
        message_data = {
            'type': 'message'}
        text = message.get('text')
        try:
            text = ast.literal_eval(text)
            if hasattr(text, 'get'):
                if text.get('action_body'):
                    message_data.update({
                        'type': 'action_body',
                        'action_body': text.get('action_body'), })
                    text = text.get('text')
        except Exception as e:
            _logger.debug(e)
        text = str(text)
        message_data.update({'text': text})
        return message_data

    def viber_utm_data(self, index):
        self.ensure_one()
        if index:
            link_tracker = self.env['link.tracker'].search([
                ('id', '=', index)])
            if link_tracker:
                self.sudo().lint_tracker_id = link_tracker

    def send_message(self, text, **kwargs):
        self.ensure_one()
        if self.chat_id.messenger_id.provider != 'viber':
            return super().send_message(text, **kwargs)
        bot = self.chat_id.viber_get_viber_bot()
        rich_media = kwargs.get('rich_media')
        keyboard = kwargs.get('keyboard')
        self.is_viber_send = True
        try:
            if rich_media:
                res = bot.send_messages(self.sender_id.viber_id, [
                    RichMediaMessage(min_api_version=2,
                                     alt_text=text,
                                     rich_media=rich_media)])
                self.viber_create_log(name='OUT', body=res)
                data = {'buttons': [self.get_button_title(i.get('Text'))
                                    for i in rich_media.get('Buttons')]}
            elif keyboard:
                res = bot.send_messages(self.sender_id.viber_id, [
                    KeyboardMessage(min_api_version=7,
                                    tracking_data='tracking_data',
                                    keyboard=keyboard)])
                self.viber_create_log(name='OUT', body=res)
                data = {'text': text}
            else:
                res = bot.send_messages(self.sender_id.viber_id, [
                    TextMessage(text=text)])
                self.viber_create_log(name='OUT', body=res)
                data = {'text': text}
            if not self.wired_conversation_id:
                self.viber_out_message(text=data)
        except Exception as e:
            _logger.info(e)
            if 'notSubscribed' in str(e):
                self.active = False
            res = False
        return res

    def send_rich_media_buttons_in_batches(self, buttons):
        batch_size = 7
        for i in range(0, len(buttons), batch_size):
            batch = buttons[i:i + batch_size]
            if self.last_step_id:
                rich_media = self.last_step_id.get_viber_rich_media(
                    text=False, buttons=batch)
                _logger.info(rich_media)
                if rich_media and batch:
                    self.send_message(text='rich_media', rich_media=rich_media)
        return True

    def get_button_title(self, text):
        self.ensure_one()
        title = re.findall('>[^"]*</', text)
        if title:
            title = re.sub("[></]", "", title[0])
            return title
        return text

    # pylint: disable=R1711
    def viber_out_message(self, text=False):
        if not self.wired_conversation_id and not self.operator_live_id:
            self.ensure_one()
            sender = self.env['kw.chatbot.sender'].search([
                ('name', '=', 'ViberBot')], limit=1)
            self.env['kw.chatbot.message'].sudo().create({
                'conversation_id': self.id, 'is_bot_message': True,
                'sender_id': sender[0].id, 'text': text,
                'name': 'None', })
        return None

    def viber_create_log(self, name=False, body=False):
        self.ensure_one()
        self.env['kw.chatbot.log'].create({
            'name': name,
            'messenger_id':  self.chat_id.messenger_id.id,
            'body': body,
            'chat_id': self.chat_id.id,
            'dialog_id': self.dialog_id.id,
            'sender_id': self.sender_id.id,
            'conversation_id': self.id, })

    @api.model
    def get_or_create(self, chat, **kwargs):
        if chat.messenger_id.provider != 'viber':
            return super().get_or_create(chat, **kwargs)
        message = kwargs.get('message')
        sender = kwargs.get('sender')
        if not message:
            raise ValueError('Cant process: "message" not provided')
        conversation = self.sudo().search([
            ('viber_id', '=', sender.viber_id),
            ('company_id', '=', chat.company_id.id),
            ('chat_id', '=', chat.id)], limit=1)
        # _logger.info(conversation)
        if not conversation:
            conversation = self.sudo().create({
                'name': sender.name,
                'viber_id': sender.viber_id,
                'dialog_id': chat.dialog_id.id,
                'sender_id': sender.id,
                'company_id': chat.company_id.id,
                'chat_id': chat.id})

            if conversation.dialog_id.is_partner:
                self.get_or_create_partner(
                    sender_id=conversation.sender_id,
                    company_id=chat.company_id)
                conversation.create_live_chat_channel(
                    conversation.sender_id.partner_id)

        return conversation

    def viber_pre_response(self, bot, message):
        self.ensure_one()

    # pylint: disable=R1710
    def viber_get_response(self, bot, message):
        self.ensure_one()
        # _logger.info('Conversation viber_get_response')
        # _logger.info(message)

        if self.dialog_id.bots_type == 'is_consultant_bot':
            if not self.sender_id.aproved_consultant and \
                    not self.sender_id.is_chatbot_consultant:
                self.send_message(
                    text='Ask an administrator to make you a consultant')
                self.write({'is_viber_send': True})
                return
            text = message.get('text')
            if text in ['/start', '/end']:
                if text == '/start':
                    self.sender_id.is_ready_for_consult = True
                    self.send_message(text='You OnLine')
                if text == '/end':
                    self.sender_id.is_ready_for_consult = False
                    self.send_message(text='You OffLine')
            self.write({'is_viber_send': True})
        self.viber_pre_response(bot=bot, message=message)
        if self.is_viber_send:
            return
        if message.get('media'):
            return True
        if not self.is_viber_send and \
                message.get('text')[:4] != 'http':
            self.viber_does_not_found()
        return False

    def send_file(self, files, **kwargs):
        self.ensure_one()
        if self.chat_id.messenger_id.provider != 'viber':
            return super().send_file(files, **kwargs)
        bot = self.chat_id.viber_get_viber_bot()
        for file in files:
            url = self.viber_get_attachment_url(file)
            res = bot.send_messages(
                self.sender_id.viber_id, [
                    FileMessage(
                        min_api_version=2,
                        media=url,
                        size=file.file_size,
                        file_name=file.name)])
            self.viber_create_log(name='OUT', body=res)
        return None

    def viber_get_attachment_url(self, attachment):
        burl = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        token = attachment.generate_access_token()
        token = token[0] if token else ''
        url = '{}/web/content/ir.attachment/{}/datas?access_token={}'.format(
            burl, attachment.id, token)
        return url

    def viber_does_not_found(self):
        buttons = self.env['kw.chatbot.default.viber.buttons']
        def_setting = buttons.search([
            ('is_used', '=', True),
            ('button_type', '=', 'keyboard')], limit=1)
        keyboard = {
            "Type": "keyboard",
            "DefaultHeight": False,
            "InputFieldState": 'hidden',
            "Buttons": [{"Columns": 6,
                         "Rows": 1,
                         "ActionType": "reply",
                         "ActionBody": str(
                             {'text': self.chat_id.viber_start_button_name
                              if self.chat_id else 'Start',
                              'action_body': '/start'}),
                         "TextHAlign":
                             'middle' if not def_setting else
                             def_setting[0].text_halign,
                         "BgColor": '#d9d9d9' if not def_setting else
                         def_setting[0].bg_btn_color,
                         "Text": '<font color="{}">Start</font>'.format(
                             ('#1d2327' if not def_setting else
                              def_setting[0].tx_color)),
                         "TextVAlign": 'center', }]}
        self.send_message(
            text='Не можливо нічого знайти за вашим запитом =(',
            keyboard=keyboard)


class Message(models.Model):
    _inherit = 'kw.chatbot.message'

    viber_id = fields.Char()

    raw_json = fields.Text()
