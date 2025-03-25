import logging

from telebot import types
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

telegram_routes = [
    '/kw_chatbot/telegram/bot/<int:chat_id>/<access_token>',
]


# pylint: disable=lost-exception
class TelegramBotRouting(http.Controller):

    @http.route(telegram_routes, type='json', auth='public',
                methods=['POST'], csrf=False, )
    def kw_chatbot_telegram_bot_chat_id_post(
            self, chat_id=None, access_token=None, **kwargs):
        try:
            return 'ok'
        finally:
            chat = request.env['kw.chatbot.chat'].sudo().search([
                ('telegram_access_token', '=', access_token),
                ('id', '=', chat_id), ], limit=1)
            jsonrequest = http.request.get_json_data()
            log = request.env['kw.chatbot.log'].sudo().create({
                'name': 'IN',
                'messenger_id': chat.messenger_id.id if chat else False,
                'url': http.request.httprequest.url,
                'method': http.request.httprequest.method,
                'headers': http.request.httprequest.headers,
                'body': jsonrequest,
                'chat_id': chat.id if chat else False,
                'dialog_id': chat.dialog_id.id if chat else False,
            })
            # pylint: disable=E8102
            request._cr.commit()
            if not chat:
                return 'error'
            chat.log_id = log.id
            chat.telegram_get_telegram_bot().process_new_updates(
                [types.Update.de_json(jsonrequest)])
