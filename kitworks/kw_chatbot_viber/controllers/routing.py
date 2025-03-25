import logging


from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


viber_routes = [
    '/kw_chatbot/viber/bot/<int:chat_id>/<access_token>',
]


# pylint: disable=lost-exception
class ViberBotRouting(http.Controller):

    @http.route(viber_routes, type='json', auth='public',
                methods=['POST'], csrf=False,)
    def kw_chatbot_viber_bot_chat_id_post(
            self, chat_id=None, access_token=None, **kwargs):
        try:
            return Response(status=200)
        finally:
            _logger.info('___________________________________________________')

            chat = request.env['kw.chatbot.chat'].sudo().search([
                ('viber_access_token', '=', access_token),
                ('id', '=', chat_id), ], limit=1)
            if not chat:
                return 'error'
            viber_request = http.request.get_json_data()
            chatbot_message = request.env['kw.chatbot.message'].sudo().search([
                ('name', '=', viber_request.get('message_token'))], limit=1)
            if not chatbot_message:
                _logger.info('______________________________________________')
                _logger.info(viber_request)
                _logger.info(chatbot_message)
                _logger.info('______________________________________________')
                log = request.env['kw.chatbot.log'].sudo().create({
                    'name': 'IN',
                    'messenger_id': chat.messenger_id.id if chat else False,
                    'url': http.request.httprequest.url,
                    'method': http.request.httprequest.method,
                    'headers': http.request.httprequest.headers,
                    'body': viber_request,
                    'chat_id': chat.id if chat else False,
                    'dialog_id': chat.dialog_id.id if chat else False,
                })
                chat.viber_value_query_handler(viber_request, log)
