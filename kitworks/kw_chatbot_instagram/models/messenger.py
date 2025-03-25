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

    instagram_copy_url = fields.Char()
    instagram_verify_token = fields.Char()
    instagram_webhook_token = fields.Char()

    instagram_app_name = fields.Char(
        readonly=True, string='App Name', )
    instagram_app_access_token = fields.Char(
        string='Facebook App Access Token',
        default=lambda self: self._default_get(
            'kw_facebook_app_access_token') or '', )
    instagram_app_id = fields.Char(
        readonly=True, string='Facebook App ID',
        default=lambda self: self._default_get(
            'kw_facebook_app_id') or '', )
    instagram_app_secret = fields.Char(
        string='Facebook App Secret',
        default=lambda self: self._default_get(
            'kw_facebook_app_secret') or '', )
    is_instagram_app_connect = fields.Boolean(
        default=False, readonly=True, )
    instagram_connect_msg = fields.Char(
        default='The application is not connected to the system',
        readonly=True, )

    is_instagram_webhook_connect = fields.Boolean(
        default=False, readonly=True, )
    instagram_webhook_msg = fields.Char(
        readonly=True, )

    instagram_sdk_token = fields.Char()

    is_instagram_login = fields.Boolean(
        default=True, )

    _sql_constraints = [
        ('instagram_sdk_token_unique', 'unique(instagram_sdk_token)',
         'Instagram SDK Token should be unique'), ]

    def instagram_login(self):
        self.ensure_one()
        if not self.instagram_sdk_token:
            raise exceptions.ValidationError(
                _('Instagram app is not configured'))
        return {
            'type': 'ir.actions.act_url',
            'name': "Instagram Login",
            'target': '_blank',
            'url': '/kw/instagram/login/%s/%s' % (
                self.id, self.instagram_sdk_token,)}

    @api.model
    def instagram_generate_verify_token(self):
        r_bytes = os.urandom(16)
        return str(hashlib.sha256(r_bytes).hexdigest())

    def instagram_app_connect(self):
        params = {'access_token': self.instagram_app_access_token}
        app_data = FacebookGraphApi().get_facebook_graph(
            url='/app', params=params)
        if app_data.get('data'):
            self.write({
                'is_instagram_app_connect': True,
                'instagram_app_name': app_data['data'].get('name'),
                'instagram_connect_msg': 'Connect',
                'instagram_app_id': app_data['data'].get('id'),
                'is_instagram_webhook_connect': False,
                'instagram_verify_token':
                    self.instagram_generate_verify_token(),
                'instagram_copy_url': self.get_instagram_copy_url(),
                'instagram_sdk_token':
                    self.instagram_generate_verify_token(), })
        else:
            self.write({
                'is_instagram_app_connect': False,
                'instagram_connect_msg': app_data.get('error'), })

    def get_instagram_copy_url(self):
        burl = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        self.write({
            'instagram_webhook_token': self.instagram_generate_verify_token()})
        return '{}/kw_chatbot/instagram/bot/{}'.format(
            burl, self.instagram_webhook_token)

    def instagram_update_webhook(self):
        if not self.instagram_copy_url or not self.instagram_verify_token:
            raise exceptions.ValidationError(
                _('Instagram Copy Url or Instagram Verify Token are missing'))
        self.is_instagram_webhook_connect = False
        body = {
            'access_token': self.instagram_app_access_token,
            'object': 'instagram',
            'fields': ['messages'],
            'callback_url': self.instagram_copy_url,
            'verify_token': self.instagram_verify_token, }
        app_data = FacebookGraphApi().post_facebook_graph(
            url='/v14.0/app/subscriptions', body=body)
        if app_data.get('data'):
            self.write({
                'instagram_webhook_msg': app_data.get('data'),
                'is_instagram_webhook_connect': True, })
            chat_ids = self.env['kw.chatbot.chat'].sudo().search([
                ('instagram_app_id', '=', self.instagram_app_id),
                ('is_instagram_login', '=', True), ])
            for chat in chat_ids:
                chat.write({
                    'instagram_copy_url': self.instagram_copy_url,
                    'instagram_verify_token': self.instagram_verify_token,
                    'instagram_webhook_token': self.instagram_webhook_token, })
        else:
            self.write({
                'is_instagram_webhook_connect': False,
                'instagram_webhook_msg': app_data.get('error'), })

    def add_instagram_account(self, access_token):
        params = {'access_token': access_token}
        account_data = FacebookGraphApi().get_facebook_graph(
            url='/me/accounts', params=params)
        if account_data.get('data'):
            for account in account_data['data'].get('data'):
                instagram_account_id = self.get_instagram_business_account(
                    access_token=account.get('access_token'))
                chat_id = self.env['kw.chatbot.chat'].sudo().search([
                    ('facebook_page_account_id', '=', account.get('id')),
                    ('provider', '=', 'instagram'), ])
                if instagram_account_id:
                    if not chat_id:
                        chat_id = self.instagram_create_chat(
                            instagram_account=account,
                            instagram_account_id=instagram_account_id)
                        chat_id.get_instagram_name()
                    chat_id.get_instagram_long_lived_token()
                    chat_id.instagram_subscribed_fields()
                    chat_id.write({
                        'active': True,
                        'instagram_copy_url': self.instagram_copy_url,
                        'instagram_verify_token':
                            self.instagram_verify_token,
                        'instagram_webhook_token':
                            self.instagram_webhook_token, })
                else:
                    chat_id.write({'active': False})

    def get_instagram_business_account(self, access_token):
        params = {'access_token': access_token,
                  'fields': 'instagram_business_account'}
        instagram_business_account = FacebookGraphApi().get_facebook_graph(
            url='/me', params=params)
        if instagram_business_account.get('data'):
            data = instagram_business_account['data']
            instagram_business_account = data.get('instagram_business_account')
            if instagram_business_account:
                return data['instagram_business_account'].get('id')
        return False

    def instagram_create_chat(self, instagram_account, instagram_account_id):
        chat = self.env['kw.chatbot.chat'].sudo()
        dialog_id = self.env['kw.chatbot.dialog'].sudo().search([
            ('bots_type', '=', 'is_consultant_bot')], limit=1)
        if instagram_account:
            data = {
                'name': instagram_account.get('name'),
                'messenger_id': self.id,
                'dialog_id': dialog_id.id,
                'is_instagram_login': True,
                'instagram_app_id': self.instagram_app_id,
                'instagram_app_secret': self.instagram_app_secret,
                'instagram_account_id': instagram_account_id,
                'facebook_page_account_id': instagram_account.get('id'),
                'instagram_access_token':
                    instagram_account.get('access_token'),
                'instagram_copy_url': self.instagram_copy_url,
                'instagram_verify_token': self.instagram_verify_token,
                'instagram_webhook_token': self.instagram_webhook_token, }
            chat = chat.create(data)
        return chat

    def instagram_check_sub_in_app(self, access_token):
        params = {'access_token': access_token}
        account_data = FacebookGraphApi().get_facebook_graph(
            url='/me/subscribed_apps', params=params)
        if account_data.get('data'):
            for app in account_data['data'].get('data'):
                if self.instagram_app_id == app.get('id'):
                    return True
        return False
