# flake8: noqa: E501
import base64
import logging
import mimetypes
import requests
# pylint: disable=C0411
from urllib.parse import urlparse
import socket
from telebot import types

from odoo import models, fields
from odoo.tools.mimetypes import guess_mimetype

_logger = logging.getLogger(__name__)


class Notification(models.Model):
    _inherit = 'kw.chatbot.notification'

    tg_url_name = fields.Text(
        string='URL Name', default='Link')  # todo: translate=True
    send_location_name = fields.Text(
        default='Send Location', translate=True)
    is_tg_send_location = fields.Boolean(
        default=False, string='Send Location')

    @staticmethod
    def is_local_ip(ip):
        local_ips = ["192.168.", "10.", "127.0.0.1", "127.0.1.1"]
        return any(ip.startswith(local) for local in local_ips)

    def prepare_url(self, url):
        burl = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        if not url.lower().startswith(('http://', 'https://')):
            url = burl.rstrip('/') + '/' + url.lstrip('/')
        return url

    @staticmethod
    def is_url_working(url):
        try:
            response = requests.get(url, timeout=20)
            if 200 <= response.status_code < 300:
                parsed_url = urlparse(url)
                hostname = parsed_url.hostname
                ip = socket.gethostbyname(hostname)
                return not Notification.is_local_ip(ip)
        except requests.RequestException:
            _logger.info('Bad Request: inline keyboard button URL')
        return False

    # pylint: disable=R0914,R0912
    def send_message(self, record, text, conversation_id, **kwargs):
        provider = conversation_id.chat_id.messenger_id.provider
        if provider == 'telegram':
            reply_markup = kwargs.get('reply_markup')
            if not reply_markup:
                reply_markup = types.InlineKeyboardMarkup()
            if self.is_add_url:
                burl = self.env['ir.config_parameter'].sudo().get_param(
                    'web.base.url')
                if self.is_developer_mode:
                    burl = self.developer_url.strip()
                url = "{}/web#id={}&model={}&view_type=form".format(
                    burl, record.id, record._name)
                if self.is_url_working(url):
                    btn = types.InlineKeyboardButton(
                        text=self.tg_url_name, url=url)
                    reply_markup.add(btn)
                    kwargs.update({
                        'record_url': True,
                        'reply_markup': reply_markup,})
            if self.use_image_product and record.image_1920 \
                    and kwargs.get('bot'):
                bot = kwargs.get('bot')
                bot.send_photo(
                    conversation_id.telegram_id,
                    base64.b64decode(record.image_1920),
                    caption=text, reply_markup=kwargs.get('reply_markup'), )
                return None
            if self.is_tg_send_location:
                buttons_names = []
                reply_markup = types.ReplyKeyboardMarkup(
                    resize_keyboard=True)
                buttons = types.KeyboardButton(
                    text=self.send_location_name,
                    request_location=True)
                reply_markup.add(buttons)
                buttons_names.append(self.send_location_name)
                kwargs.update({
                    'buttons': buttons_names,
                    'reply_markup': reply_markup, })
        res = super().send_message(record, text, conversation_id, **kwargs)

        if self.is_file_send and self.file_fields_ids:
            for file_field in self.file_fields_ids:
                file = getattr(record, file_field.name)
                if file and provider == 'telegram':
                    if file_field.ttype == 'binary':
                        file = base64.b64decode(file)
                        mime_type = mimetypes.guess_extension(
                            guess_mimetype(file))
                        f_name = 'Report'
                        if hasattr(record, 'name'):
                            f_name = record.name
                        conversation_id.telegram_send_file(
                            file= file,
                            filename=f'{f_name}.{mime_type}')
                    else:
                        conversation_id.send_file(files=file)
        return res
