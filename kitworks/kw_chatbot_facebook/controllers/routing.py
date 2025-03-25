import logging

import json
from odoo import http
from odoo.http import request
from odoo.tools.misc import file_open

_logger = logging.getLogger(__name__)

facebook_api_url = 'https://graph.facebook.com/v14.0'
facebook_routes = [
    '/kw_chatbot/facebook/bot/<webhook_token>',
]


class FacebookBotRouting(http.Controller):

    @http.route(facebook_routes, type='http', auth='public',
                methods=['GET'], csrf=False, )
    def kw_chatbot_facebook_bot_chat_id_get(
            self, webhook_token=None, **kwargs):
        chat = request.env['kw.chatbot.chat'].sudo().search([
            ('facebook_webhook_token', '=', webhook_token), ], limit=1)
        messenger = request.env['kw.chatbot.messenger'].sudo()
        if not chat:
            messenger = messenger.search([
                ('facebook_webhook_token', '=', webhook_token), ], limit=1)
            if not messenger:
                # _logger.info('Wrong chat connection')
                return 'Invalid url'
        verify_token = chat.facebook_verify_token if chat \
            else messenger.facebook_verify_token
        token_sent = kwargs.get('hub.verify_token')
        if token_sent == verify_token:
            return kwargs.get('hub.challenge')
        return 'Invalid verification token'

    @http.route(facebook_routes, type='json', auth='public',
                methods=['POST'], csrf=False, )
    def kw_chatbot_facebook_bot_chat_id_post(
            self, webhook_token=None, **kwargs):
        try:
            return "success"
        finally:
            logging.info(http.request.jsonrequest)
            jsonrequest = http.request.get_json_data()
            data = jsonrequest.get('entry')
            chat = request.env['kw.chatbot.chat'].sudo().search([
                ('active', '=', True),
                ('facebook_webhook_token', '=', webhook_token),
                ('facebook_account_id', '=', data[0].get('id')), ], limit=1)
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
                chat.facebook_process_call(jsonrequest, log)


class FacebookSdk(http.Controller):

    @http.route('/kw/facebook/login/<int:messenger_id>/'
                '<string:facebook_sdk_token>',
                type='http', auth="public", website=True,
                sitemap=False, csrf=False, )
    def facebook_login(self, messenger_id, facebook_sdk_token, **post):
        messenger = request.env['kw.chatbot.messenger'].sudo().search([
            ('id', '=', messenger_id), ], limit=1)
        data = post.get('data')
        if not data:
            with file_open("kw_chatbot_facebook/static/src/"
                           "facebook_login.html", "r") as fd:
                template = fd.read().replace(
                    'facebook_app_id', messenger.facebook_app_id, )
            return template
        data = json.loads(data)
        if data.get('authResponse') and messenger:
            messenger.add_facebook_account(
                access_token=data['authResponse'].get('accessToken'))
            return 'ok'
        _logger.info(data)
        return False
