import hashlib
import logging
import os

from odoo import models, fields, api, exceptions, _
from odoo.addons.kw_graph_api.models.graph_api import FacebookGraphApi

_logger = logging.getLogger(__name__)


class Messenger(models.Model):
    _inherit = 'kw.chatbot.messenger'

    def _default_get(self, vals):
        params = self.env['ir.config_parameter'].sudo().get_param(
            vals) or False
        if params:
            if all(x.isdigit() for x in params.split()):
                return int(params)
        return params

    facebook_copy_url = fields.Char()
    facebook_verify_token = fields.Char()
    facebook_webhook_token = fields.Char()

    facebook_app_name = fields.Char(
        readonly=True, string='App Name')
    facebook_app_access_token = fields.Char(
        default=lambda self: self._default_get(
            'kw_facebook_app_access_token') or '', )
    facebook_app_id = fields.Char(
        readonly=True, string='Facebook App ID',
        default=lambda self: self._default_get(
            'kw_facebook_app_id') or '', )
    facebook_app_secret = fields.Char(
        default=lambda self: self._default_get(
            'kw_facebook_app_secret') or '', )
    is_facebook_app_connect = fields.Boolean(
        default=False, readonly=True, )
    facebook_connect_msg = fields.Char(
        default='The application is not connected to the system',
        readonly=True, )

    is_facebook_webhook_configure = fields.Boolean(
        default=False, )

    is_facebook_webhook_connect = fields.Boolean(
        default=False, readonly=True, )
    facebook_webhook_msg = fields.Char(
        readonly=True, )

    facebook_sdk_token = fields.Char()

    is_facebook_login = fields.Boolean(
        default=True, )

    _sql_constraints = [
        ('facebook_sdk_token_unique', 'unique(facebook_sdk_token)',
         'Facebook SDK Token should be unique'), ]

    def facebook_login(self):
        self.ensure_one()
        if not self.facebook_sdk_token:
            raise exceptions.ValidationError(
                _('Facebook app is not configured'))
        return {
            'type': 'ir.actions.act_url',
            'name': "Facebook Login",
            'target': '_blank',
            'url': '/kw/facebook/login/%s/%s' % (
                self.id, self.facebook_sdk_token,)}

    @api.model
    def facebook_generate_verify_token(self):
        r_bytes = os.urandom(16)
        return str(hashlib.sha256(r_bytes).hexdigest())

    def facebook_app_connect(self):
        params = {'access_token': self.facebook_app_access_token}
        app_data = FacebookGraphApi().get_facebook_graph(
            url='/app', params=params)
        if app_data.get('data'):
            self.write({
                'is_facebook_app_connect': True,
                'facebook_app_name': app_data['data'].get('name'),
                'facebook_connect_msg': 'Connect',
                'facebook_app_id': app_data['data'].get('id'),
                'is_facebook_webhook_connect': False,
                'facebook_verify_token': self.facebook_generate_verify_token(),
                'facebook_copy_url': self.get_facebook_copy_url(),
                'facebook_sdk_token': self.facebook_generate_verify_token(), })
        else:
            self.write({
                'is_facebook_app_connect': False,
                'facebook_connect_msg': app_data.get('error'), })

    def get_facebook_copy_url(self):
        burl = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        self.write({
            'facebook_webhook_token': self.facebook_generate_verify_token()})
        return '{}/kw_chatbot/facebook/bot/{}'.format(
            burl, self.facebook_webhook_token)

    def facebook_webhook_fields(self, f_object, f_fields):
        body = {
            'access_token': self.facebook_app_access_token,
            'object': f_object,
            'fields': f_fields,
            'callback_url': self.facebook_copy_url,
            'verify_token': self.facebook_verify_token, }
        return body

    def facebook_update_webhook(self):
        if not self.facebook_copy_url or not self.facebook_verify_token:
            raise exceptions.ValidationError(
                _('Facebook Copy Url or Facebook Verify Token are missing'))
        self.is_facebook_webhook_connect = False
        body = self.facebook_webhook_fields(
            f_object='page', f_fields=['messages'])
        app_data = FacebookGraphApi().post_facebook_graph(
            url='/v14.0/app/subscriptions', body=body)
        if app_data.get('data'):
            self.write({
                'facebook_webhook_msg': app_data.get('data'),
                'is_facebook_webhook_connect': True, })
            chat_ids = self.env['kw.chatbot.chat'].sudo().search([
                ('facebook_app_id', '=', self.facebook_app_id),
                ('is_facebook_login', '=', True), ])
            for chat in chat_ids:
                chat.write({
                    'facebook_copy_url': self.facebook_copy_url,
                    'facebook_verify_token': self.facebook_verify_token,
                    'facebook_webhook_token': self.facebook_webhook_token, })
        else:
            self.write({
                'is_facebook_webhook_connect': False,
                'facebook_webhook_msg': app_data.get('error'), })

    def add_facebook_account(self, access_token):
        params = {'access_token': access_token}
        account_data = FacebookGraphApi().get_facebook_graph(
            url='/me/accounts', params=params)
        if account_data.get('data'):
            for account in account_data['data'].get('data'):
                chat_id = self.env['kw.chatbot.chat'].sudo().search([
                    ('facebook_account_id', '=', account.get('id'))
                ], limit=1)
                # if self.facebook_check_sub_in_app(
                #         access_token=account.get('access_token')):
                if not chat_id:
                    chat_id = self.facebook_create_chat(
                        facebook_account=account)
                chat_id.get_facebook_long_lived_token()
                if self.is_facebook_webhook_configure:
                    chat_id.facebook_subscribed_fields()
                chat_id.write({
                    'active': True,
                    'facebook_copy_url': self.facebook_copy_url,
                    'facebook_verify_token': self.facebook_verify_token,
                    'facebook_webhook_token': self.facebook_webhook_token})
            # else:
            #     chat_id.write({'active': False})

    def facebook_create_chat(self, facebook_account):
        chat = self.env['kw.chatbot.chat'].sudo()
        dialog_id = self.env['kw.chatbot.dialog'].sudo().search([
            ('bots_type', '=', 'is_consultant_bot')], limit=1)
        if facebook_account:
            data = {
                'name': facebook_account.get('name'),
                'messenger_id': self.id,
                'dialog_id': dialog_id.id,
                'is_facebook_login': True,
                'facebook_app_id': self.facebook_app_id,
                'facebook_app_secret': self.facebook_app_secret,
                'facebook_account_id': facebook_account.get('id'),
                'facebook_access_token': facebook_account.get('access_token'),
                'facebook_copy_url': self.facebook_copy_url,
                'facebook_verify_token': self.facebook_verify_token,
                'facebook_webhook_token': self.facebook_webhook_token, }
            chat = chat.create(data)
        return chat

    # def facebook_check_sub_in_app(self, access_token):
    #     params = {'access_token': access_token}
    #     account_data = FacebookGraphApi().get_facebook_graph(
    #         url='/me/subscribed_apps', params=params)
    #     if account_data.get('data'):
    #         _logger.info(account_data.get('data'))
    #         for app in account_data['data'].get('data'):
    #             if self.facebook_app_id == app.get('id'):
    #                 return True
    #     else:
    #         return False
