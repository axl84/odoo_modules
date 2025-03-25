import logging

from odoo.http import request
from odoo import http

_logger = logging.getLogger(__name__)

echat_incoming_routes = [
    '/kw_chatbot/echat/incoming/<int:chat_id>', ]
echat_outgoing_routes = [
    '/kw_chatbot/echat/outgoing/<int:chat_id>', ]


# pylint: disable=too-many-locals, too-many-branches, too-many-statements
class EchatRouting(http.Controller):

    @http.route(echat_incoming_routes, type='json', auth='public',
                methods=['POST'], csrf=False, )
    def kw_chatbot_echat_bot_chat_id_post(self, chat_id=None, **kwargs):
        try:
            return 'ok'
        finally:
            jsonrequest = http.request.get_json_data()
            chat = request.env['kw.chatbot.chat'].sudo().search([
                ('id', '=', chat_id)], limit=1)
            if chat:
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
                chat.echat_process_call(
                    jsonrequest=jsonrequest, log=log)
