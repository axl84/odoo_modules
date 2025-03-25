import logging

import json
from odoo import http
from odoo.http import request
from odoo.tools.misc import file_open

_logger = logging.getLogger(__name__)

facebook_page_routes = [
    '/kw/page/facebook/webhook/<webhook_token>',
]
instagram_page_routes = [
    '/kw/instagram/webhook/<webhook_token>',
]


class FacebookSdk(http.Controller):

    @http.route('/kw/facebook/login/<int:app_id>/'
                '<string:identifier>/<string:facebook_sdk_token>',
                type='http', auth="public", website=True,
                sitemap=False, csrf=False, )
    def facebook_login(
            self, app_id, identifier, facebook_sdk_token, **post):
        app = request.env['kw.facebook.app'].sudo().search([
            ('id', '=', app_id), ], limit=1)
        data = post.get('data')
        if not data:
            with file_open("kw_graph_api/static/src/"
                           "facebook_login.html", "r") as fd:
                template = fd.read().replace(
                    'facebook_app_id', app.app_id, ).replace(
                    'facebook_return_url', app.facebook_return_url, ).replace(
                    'facebook_permission', post.get('permission'))
            return template
        data = json.loads(data)
        if data.get('authResponse') and app and identifier:
            app.add_page(
                access_token=data['authResponse'].get('accessToken'),
                identifier=identifier)
            return 'ok'
        _logger.info(data)
        return False


class FacebookWebhookRouting(http.Controller):

    @http.route(facebook_page_routes, type='http', auth='public',
                methods=['GET'], csrf=False, )
    def kw_facebook_page_webhook_routing_get(
            self, webhook_token=None, **kwargs):
        app = request.env['kw.facebook.app'].sudo().search([
            ('page_webhook_token', '=', webhook_token), ], limit=1)
        if not app:
            return 'Invalid url'
        token_sent = kwargs.get('hub.verify_token')
        if token_sent == app.page_verify_token:
            return kwargs.get('hub.challenge')
        return 'Invalid verification token'

    @http.route(instagram_page_routes, type='http', auth='public',
                methods=['GET'], csrf=False, )
    def kw_facebook_instagram_webhook_routing_get(
            self, webhook_token=None, **kwargs):
        app = request.env['kw.facebook.app'].sudo().search([
            ('instagram_webhook_token', '=', webhook_token), ], limit=1)
        if not app:
            return 'Invalid url'
        token_sent = kwargs.get('hub.verify_token')
        if token_sent == app.instagram_verify_token:
            return kwargs.get('hub.challenge')
        return 'Invalid verification token'

    @http.route(facebook_page_routes, type='json', auth='public',
                methods=['POST'], csrf=False, )
    def kw_facebook_page_webhook_post(
            self, webhook_token=None, **kwargs):
        try:
            return "ok"
        finally:
            data = http.request.jsonrequest.get('entry')
            page_id = request.env['kw.facebook.page'].sudo().search([
                ('page_webhook_token', '=', webhook_token),
                ('net_object', '=', 'page'), ], limit=1)
            self.facebook_page_handler(
                data=data, httprequest=http.request.jsonrequest,
                webhook_token=webhook_token, page_id=page_id)

    def facebook_page_handler(self, page_id, data, httprequest, webhook_token):
        logging.info(data)
        return False

    @http.route(instagram_page_routes, type='json', auth='public',
                methods=['POST'], csrf=False, )
    def kw_facebook_instagram_webhook_post(
            self, webhook_token=None, **kwargs):
        try:
            return "ok"
        finally:
            data = http.request.jsonrequest.get('entry')
            page_id = request.env['kw.facebook.page'].sudo().search([
                ('instagram_webhook_token', '=', webhook_token),
                ('net_object', '=', 'instagram'), ], limit=1)
            self.instagram_page_handler(
                data=data, httprequest=http.request.jsonrequest,
                webhook_token=webhook_token, page_id=page_id)

    def instagram_page_handler(
            self, page_id, data, httprequest, webhook_token):
        logging.info(data)
        return False
