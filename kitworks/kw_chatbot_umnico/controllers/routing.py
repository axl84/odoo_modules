import logging

from odoo.http import request
from odoo import http

_logger = logging.getLogger(__name__)


# pylint: disable=too-many-locals, too-many-branches, too-many-statements
class ApiController(http.Controller):

    @http.route('/message/chat/umnico/<int:messenger_id>', type='json',
                auth='public', chat_id=None, methods=['POST'], csrf=False, )
    def webhook_message_chat_customer(self, messenger_id=None, **kwargs):
        try:
            return "success"
        finally:
            jsonrequest = http.request.get_json_data()
            if jsonrequest.get("type") == "message.incoming":
                messenger = request.env['kw.chatbot.messenger'].sudo().search([
                    ('id', '=', messenger_id), ], limit=1)
                chat = messenger.chatbot_chat_ids[0]
                if not chat:
                    chat = request.env[
                        'kw.chatbot.chat'].sudo().umnico_create_chat()
                log = request.env['kw.chatbot.log'].sudo().create({
                    'name': 'IN',
                    'messenger_id': chat.messenger_id.id if chat else False,
                    'url': http.request.httprequest.url,
                    'method': http.request.httprequest.method,
                    'headers': http.request.httprequest.headers,
                    'chat_id': chat.id if chat else False,
                    'body': jsonrequest,
                    'dialog_id': chat.dialog_id.id if chat else False, })
                chat.umnico_process_call(
                    jsonrequest=jsonrequest, log=log)
