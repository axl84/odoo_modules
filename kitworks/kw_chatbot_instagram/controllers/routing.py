import logging

import json
from odoo import http
from odoo.http import request
from odoo.tools.misc import file_open

_logger = logging.getLogger(__name__)

instagram_routes = [
    '/kw_chatbot/instagram/bot/<webhook_token>',
]


class InstagramBotRouting(http.Controller):

    @http.route(instagram_routes, type='http', auth='public',
                methods=['GET'], csrf=False, )
    def kw_chatbot_instagram_bot_chat_id_get(
            self, webhook_token=None, **kwargs):
        chat = request.env['kw.chatbot.chat'].sudo().search([
            ('instagram_webhook_token', '=', webhook_token), ], limit=1)
        messenger = request.env['kw.chatbot.messenger'].sudo()
        if not chat:
            messenger = messenger.search([
                ('instagram_webhook_token', '=', webhook_token), ], limit=1)
            if not messenger:
                # _logger.info('Wrong chat connection')
                return 'Invalid url'
        verify_token = chat.instagram_verify_token if chat \
            else messenger.instagram_verify_token
        token_sent = kwargs.get('hub.verify_token')
        if token_sent == verify_token:
            return kwargs.get('hub.challenge')
        return 'Invalid verification token'

    @http.route(instagram_routes, type='json', auth='public',
                methods=['POST'], csrf=False, )
    def kw_chatbot_instagram_bot_chat_id_post(
            self, webhook_token=None, **kwargs):
        try:
            return "success"
        finally:
            jsonrequest = http.request.get_json_data()
            data = jsonrequest.get('entry')

            _logger.info('Instagram Message')
            _logger.info(data)
            _logger.info('_________________________________________________')
            chat = request.env['kw.chatbot.chat'].sudo().search([
                ('active', '=', True),
                ('instagram_webhook_token', '=', webhook_token),
                ('instagram_account_id', '=', data[0].get('id')), ], limit=1)
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
            # if not chat:
            #     _logger.info('Wrong chat connection')
            if chat:
                chat.instagram_process_call(jsonrequest, log)


class FacebookInstagramSdk(http.Controller):

    @http.route('/kw/instagram/login/<int:messenger_id>/'
                '<string:instagram_sdk_token>',
                type='http', auth="public", website=True,
                sitemap=False, csrf=False, )
    def instagram_login(self, messenger_id, instagram_sdk_token, **post):
        messenger = request.env['kw.chatbot.messenger'].sudo().search([
            ('id', '=', messenger_id), ], limit=1)
        data = post.get('data')
        if not data:
            with file_open("kw_chatbot_instagram/static/src/"
                           "instagram_login.html", "r") as fd:
                template = fd.read().replace(
                    'instagram_app_id', messenger.instagram_app_id,)
            return template
        data = json.loads(data)
        if data.get('authResponse') and messenger:
            messenger.add_instagram_account(
                access_token=data['authResponse'].get('accessToken'))
            return 'ok'
        _logger.info(data)
        return None
