import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

whatsapp_bot_routes = [
    '/kw_chatbot/whatsapp/bot/<int:chat_id>',
]


class WhatsappBotRouting(http.Controller):

    @http.route(whatsapp_bot_routes, type='http', auth="public",
                website=True, sitemap=False, csrf=False, )
    def whatsapp_webhook_routing_get(
            self, chat_id=None, **kwargs):
        chat = request.env['kw.chatbot.chat'].sudo().search([
            ('id', '=', chat_id), ], limit=1)
        if not chat:
            return 'Invalid url'
        token_sent = kwargs.get('hub.verify_token')
        if token_sent == chat.whatsapp_verify_token:
            chat.write({'whatsapp_webhook_status': 'enabled'})
            return kwargs.get('hub.challenge')
        chat.write({'whatsapp_webhook_status': 'disabled'})
        return 'Invalid verification token'

    @http.route(whatsapp_bot_routes, type='json', auth='public',
                methods=['POST'], csrf=False, )
    def kw_chatbot_webhook_bot_chat_id_post(
            self, chat_id=None, **kwargs):
        try:
            return "success"
        finally:
            chat = request.env['kw.chatbot.chat'].sudo().search([
                ('id', '=', chat_id), ], limit=1)
            log = request.env['kw.chatbot.log'].sudo().create({
                'name': 'IN',
                'messenger_id': chat.messenger_id.id if chat else False,
                'url': http.request.httprequest.url,
                'method': http.request.httprequest.method,
                'headers': http.request.httprequest.headers,
                'body': http.request.jsonrequest,
                'chat_id': chat.id if chat else False,
                'dialog_id': chat.dialog_id.id if chat else False, })
            if not chat:
                _logger.info('Wrong chat connection')
            chat.whatsapp_process_call(http.request.jsonrequest, log)
