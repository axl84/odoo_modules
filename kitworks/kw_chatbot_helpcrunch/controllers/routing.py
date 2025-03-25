import logging

from odoo.http import request
from odoo import http

_logger = logging.getLogger(__name__)


# pylint: disable=too-many-locals, too-many-branches, too-many-statements
class ApiController(http.Controller):

    @http.route('/chat/new/<int:messenger_id>', type='json', auth='public',
                methods=['POST'], csrf=False, )
    def webhook_chat_new(self, messenger_id=None, **kwargs):
        try:
            return "success"
        finally:
            jsonrequest = http.request.get_json_data()
            messenger = request.env['kw.chatbot.messenger'].sudo().search([
                ('id', '=', messenger_id), ], limit=1)
            chat = messenger.chatbot_chat_ids[0]
            request.env['kw.chatbot.log'].sudo().create({
                'name': 'Create Conversation',
                'messenger_id': chat.messenger_id.id if
                chat else False,
                'url': http.request.httprequest.url,
                'method': http.request.httprequest.method,
                'headers': http.request.httprequest.headers,
                'body': jsonrequest,
                'chat_id': chat.id if chat else False,
                'dialog_id': chat.dialog_id.id if chat else False, })

    @http.route('/message/chat/customer/<int:messenger_id>', type='json',
                auth='public', chat_id=None, methods=['POST'], csrf=False, )
    def webhook_message_chat_customer(self, messenger_id=None, **kwargs):
        try:
            return "success"
        finally:
            messenger = request.env['kw.chatbot.messenger'].sudo().search([
                ('id', '=', messenger_id), ], limit=1)
            chat = messenger.chatbot_chat_ids.filtered(
                lambda x: x.dialog_id)[0]
            if not chat:
                chat = request.env[
                    'kw.chatbot.chat'].sudo().helpcrunch_create_chat()
            jsonrequest = http.request.get_json_data()
            log = request.env['kw.chatbot.log'].sudo().create({
                'name': 'IN',
                'messenger_id': chat.messenger_id.id if chat else False,
                'url': http.request.httprequest.url,
                'method': http.request.httprequest.method,
                'headers': http.request.httprequest.headers,
                'chat_id': chat.id if chat else False,
                'body': jsonrequest,
                'dialog_id': chat.dialog_id.id if chat else False, })
            chat.helpcrunch_process_call(
                jsonrequest=jsonrequest, log=log)
