from ast import literal_eval
import hashlib
import logging
import os
import base64

import requests
from viberbot import Api
from viberbot.api.bot_configuration import BotConfiguration
from viberbot.api.messages.keyboard_message import KeyboardMessage
from odoo import models, fields, api, exceptions, _

_logger = logging.getLogger(__name__)


class Chat(models.Model):
    _inherit = 'kw.chatbot.chat'

    viber_timestamp = fields.Float()

    viber_token = fields.Char()

    viber_access_token = fields.Char()

    viber_message_token = fields.Char()

    viber_update_webhook_response = fields.Text(
        readonly=True, )

    viber_developer_url = fields.Char()

    viber_start_button_name = fields.Char(
        default='Start', required=True,)

    @api.constrains('viber_token', 'messenger_id')
    def _constrain_viber_token(self):
        for obj in self:
            if not obj.messenger_id:
                continue
            if obj.messenger_id.provider != 'viber':
                continue
            if not obj.viber_token:
                raise exceptions.ValidationError(_(
                    '"Viber token" is required for Viber chat'))

    def viber_update_hook_address(self):
        self.ensure_one()
        # _logger.info('viber_update_hook_address')
        self.viber_access_token = self.viber_generate_verify_token()
        if self.viber_access_token:
            path_url = 'kw_chatbot/viber/bot/{}/{}'.format(
                self.id, self.viber_access_token)
        else:
            raise exceptions.ValidationError(_(
                '"Viber access token" is empty'))
        burl = os.path.join(self.env['ir.config_parameter'].sudo(
            ).get_param('web.base.url'), path_url)
        if self.is_developer_mode:
            burl = os.path.join(self.viber_developer_url, path_url)
        hook = 'https://chatapi.viber.com/pa/set_webhook'
        headers = {'X-Viber-Auth-Token': self.viber_token}
        sen = dict(url=burl, event_types=[
            'conversation_started', 'message'])
        # pylint: disable=E8106
        r = requests.post(url=hook, json=sen, headers=headers)
        self.viber_update_webhook_response = r.text
        account_hook = "https://chatapi.viber.com/pa/get_account_info"
        get_account = requests.post(url=account_hook, headers=headers)
        if get_account.json().get('name'):
            self.write({'name': get_account.json().get('name')})
        return True

    @api.model
    def viber_generate_verify_token(self):
        r_bytes = os.urandom(16)
        return str(hashlib.sha256(r_bytes).hexdigest())

    def viber_get_viber_bot(self):
        self.ensure_one()
        burl = os.path.join(
            self.env['ir.config_parameter'].sudo().get_param('web.base.url'),
            '/kw_chatbot_viber/static/description/icon.png')
        if self.is_developer_mode:
            burl = os.path.join(
                self.viber_developer_url,
                '/kw_chatbot_viber/static/description/icon.png')
        bot = Api(BotConfiguration(name=self.name, avatar=burl,
                                   auth_token=self.viber_token))
        return bot

    def viber_value_query_handler(self, jsonrequest, log):

        def check_context(context):
            try:
                index = int(context)
            except Exception as e:
                _logger.debug(e)
                index = False
            return index
        if check_context(jsonrequest.get('context')):
            sender = self.env['kw.chatbot.sender'].sudo().get_or_create(
                messenger=self.messenger_id, sender=jsonrequest.get('user'),
                message_token=jsonrequest.get('message_token'))
            conversation = self.env['kw.chatbot.conversation'].sudo(
            ).get_or_create(chat=self, message='context', sender=sender)
            if conversation:
                conversation.viber_utm_data(jsonrequest.get('context'))
        # _logger.info('viber_value_query_handler')
        # _logger.info(jsonrequest)
        if jsonrequest.get('event') == 'message':
            bot = self.viber_get_viber_bot()
            message = jsonrequest.get('message')
            sender = self.env['kw.chatbot.sender'].sudo().get_or_create(
                messenger=self.messenger_id, sender=jsonrequest.get('sender'),
                message_token=jsonrequest.get('message_token'))
            conversation = self.env['kw.chatbot.conversation'].sudo(
            ).get_or_create(chat=self, message=message, sender=sender)
            log.sudo().write(
                {'sender_id': sender.id,
                 'conversation_id': conversation.id})
            message_data = {
                'viber_id': sender.name,
                'conversation_id': conversation.id,
                'sender_id': sender.id, 'text': message.get('text'),
                'name': jsonrequest.get('message_token'), }
            if message.get('text'):
                if 'action_body' in message.get('text'):
                    message_data = {
                        'viber_id': sender.name,
                        'conversation_id': conversation.id,
                        'sender_id': sender.id,
                        'is_call_back_message': True,
                        'text': literal_eval(message.get('text')),
                        'name': jsonrequest.get('message_token'), }
            if message.get('media'):
                url = message.get('media')
                filename = message.get('file_name')
                att_id = self.upload_file_on_url(
                    url=url, filename=filename)
                if att_id:
                    message_data.update({'attachment_ids': [(4, att_id.id)]})
            conversation.chatbot_message_id = \
                self.env['kw.chatbot.message'].sudo().create(message_data)
            conversation.last_activity_datetime = fields.Datetime.now()
            conversation.viber_get_response(bot=bot, message=message)
        elif jsonrequest.get('event') == 'conversation_started':
            bot = self.viber_get_viber_bot()
            step = self.env['kw.chatbot.step'].sudo().search([], limit=1)
            try:
                bot.send_messages(jsonrequest.get('user').get('id'), [
                    KeyboardMessage(
                        min_api_version=7, tracking_data='tracking_data',
                        keyboard=step.get_viber_keyboard_markup('Start', []))])
            except Exception as e:
                _logger.info(e)

    def upload_file_on_url(self, url, filename):
        try:
            # pylint: disable=E8106
            r = requests.get(url, allow_redirects=True)
            data = r.content
            mimetype = r.headers.get('content-type')
            data = base64.b64encode(data)
            data = data.decode('utf-8')
        except Exception as e:
            _logger.debug(e)
            return False
        if mimetype.split('/')[0] == 'image':
            attachment = self.env['ir.attachment'].sudo().create({
                'name': filename, 'datas': data,
                'mimetype': mimetype, 'res_model': 'mail.compose.message'})
            if attachment:
                attachment.write(
                    {'name': '{}-{}'.format(filename, attachment.id)})
                return attachment
        return False
