import hashlib
import logging
import os

from odoo import models, fields, api
from .graph_api import FacebookGraphApi

_logger = logging.getLogger(__name__)

PERMISSION = 'public_profile,email,pages_manage_metadata,pages_show_list'


class FacebookApp(models.Model):
    _name = 'kw.facebook.app'
    _description = 'Facebook App'

    def _default_get(self, vals):
        params = self.env['ir.config_parameter'].sudo().get_param(
            vals) or False
        if params:
            if all(x.isdigit() for x in params.split()):
                return int(params)
        return params

    name = fields.Char(
        readonly=True, string='App Name')
    active = fields.Boolean(
        default=True, )
    facebook_app_access_token = fields.Char(
        required=True, default=lambda self: self._default_get(
            'kw_facebook_app_access_token') or '', )
    app_id = fields.Char(
        readonly=True, string='Facebook App ID',
        default=lambda self: self._default_get(
            'kw_facebook_app_id') or '', )
    facebook_app_secret = fields.Char(
        required=True, default=lambda self: self._default_get(
            'kw_facebook_app_secret') or '', )
    is_facebook_app_connect = fields.Boolean(
        default=False, readonly=True, string='Connect')
    facebook_connect_msg = fields.Char(
        default='The application is not connected to the system',
        readonly=True, )
    is_facebook_webhook = fields.Boolean(
        default=False, )

    facebook_page_ids = fields.One2many(
        comodel_name='kw.facebook.page',
        inverse_name='facebook_app_id', )

    page_ids = fields.Many2many(
        comodel_name='kw.facebook.page',
        compute='_compute_facebook_pages', )
    instagram_ids = fields.Many2many(
        comodel_name='kw.facebook.page',
        compute='_compute_facebook_pages', )

    page_copy_url = fields.Char(
        readonly=True, )
    page_verify_token = fields.Char(
        readonly=True, )
    page_webhook_token = fields.Char(
        readonly=True, )

    instagram_copy_url = fields.Char(
        readonly=True, )
    instagram_verify_token = fields.Char(
        readonly=True, )
    instagram_webhook_token = fields.Char(
        readonly=True, )

    facebook_sdk_token = fields.Char(
        readonly=True, )
    facebook_return_url = fields.Char(
        readonly=True, )

    _sql_constraints = [
        ("name_facebook_app_access_token",
         "unique (facebook_app_access_token)",
         "This App has already been added!"), ]

    def _compute_facebook_pages(self):
        for obj in self:
            instagram = obj.facebook_page_ids.filtered(
                lambda x: x.net_object == 'instagram').ids
            page = obj.facebook_page_ids.filtered(
                lambda x: x.net_object == 'page').ids
            obj.write({
                'page_ids': [(6, 0, page)],
                'instagram_ids': [(6, 0, instagram)]})

    @staticmethod
    def get_permission(identifier):
        if identifier == 'page':
            return PERMISSION
        if identifier == 'instagram':
            return '{},{}'.format(PERMISSION, 'instagram_basic')
        return False

    def create_facebook_page(self, facebook_page, identifier, token):
        page = self.env['kw.facebook.page'].sudo()
        if facebook_page:
            data = {
                'name': facebook_page.get('name'),
                'facebook_app_id': self.id,
                'page_id': facebook_page.get('id'),
                'net_object': identifier,
                'access_token': token, }
            page = page.create(data)
        return page

    def get_instagram_business_account(self, access_token):
        params = {'access_token': access_token,
                  'fields': 'instagram_business_account{id,name}'}
        instagram_business_account = FacebookGraphApi().get_facebook_graph(
            url='/me', params=params)
        if instagram_business_account.get('data'):
            data = instagram_business_account['data']
            instagram_business_account = data.get('instagram_business_account')
            if instagram_business_account:
                return data['instagram_business_account']
        return False

    def add_page(self, access_token, identifier):
        params = {'access_token': access_token}
        account_data = FacebookGraphApi().get_facebook_graph(
            url='/me/accounts', params=params)
        if account_data.get('data'):
            for account in account_data['data'].get('data'):
                token = account.get('access_token')
                if identifier == 'instagram':
                    account = self.get_instagram_business_account(token)
                if account:
                    page_id = self.env['kw.facebook.page'].sudo().search([
                        ('page_id', '=', account.get('id'))], limit=1)
                    if not page_id:
                        page_id = self.create_facebook_page(
                            facebook_page=account, identifier=identifier,
                            token=token, )
                    if self.id == page_id.facebook_app_id.id:
                        page_id.write({'access_token': token})
                        page_id.get_facebook_long_lived_token()

    def get_facebook_sdk_parameter(self):
        burl = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url')
        menu = self.env.ref('kw_graph_api.kw_facebook_main_menu').id
        return_url = "{}/web#id={}&model={}&view_type=form" \
                     "&menu_id={}".format(burl, self.id, self._name, menu)
        self.write({
            'facebook_return_url': return_url, })

    def facebook_page_login(self):
        self.ensure_one()
        self.get_facebook_sdk_parameter()
        permission = self.get_permission('page')
        if not self.facebook_sdk_token:
            self.write({
                'facebook_sdk_token': self.generate_verify_token(), })
        return {
            'type': 'ir.actions.act_url',
            'name': "Facebook Login",
            'target': 'self',
            'url': '/kw/facebook/login/%s/%s/%s?permission=%s' % (
                self.id, 'page', self.facebook_sdk_token, permission, )}

    def instagram_page_login(self):
        self.ensure_one()
        self.get_facebook_sdk_parameter()
        permission = self.get_permission('instagram')
        if not self.facebook_sdk_token:
            self.write({
                'facebook_sdk_token': self.generate_verify_token(), })
        return {
            'type': 'ir.actions.act_url',
            'name': "Facebook Login",
            'target': 'self',
            'url': '/kw/facebook/login/%s/%s/%s?permission=%s' % (
                self.id, 'instagram', self.facebook_sdk_token, permission, )}

    @api.onchange('is_facebook_webhook')
    def _onchange_webhook(self):
        for obj in self:
            if not obj.page_webhook_token:
                obj.update_page_webhook_url()
            if not obj.instagram_webhook_token:
                obj.update_instagram_webhook_url()

    def facebook_app_connect(self):
        params = {'access_token': self.facebook_app_access_token}
        app_data = FacebookGraphApi().get_facebook_graph(
            url='/app', params=params)
        if app_data.get('data'):
            self.write({
                'is_facebook_app_connect': True,
                'name': app_data['data'].get('name'),
                'facebook_connect_msg': 'Connect',
                'app_id': app_data['data'].get('id'), })
        else:
            self.write({
                'is_facebook_app_connect': False,
                'facebook_connect_msg': app_data.get('error'), })

    @api.model
    def generate_verify_token(self):
        r_bytes = os.urandom(16)
        return str(hashlib.sha256(r_bytes).hexdigest())

    def update_page_webhook_url(self):
        burl = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        facebook_page_webhook_token = self.generate_verify_token()
        webhook_url = '{}/kw/page/facebook/webhook/{}'.format(
            burl, facebook_page_webhook_token)
        self.write({
            'page_webhook_token': facebook_page_webhook_token,
            'page_copy_url': webhook_url,
            'page_verify_token': self.generate_verify_token(), })

    def update_instagram_webhook_url(self):
        burl = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        instagram_webhook_token = self.generate_verify_token()
        webhook_url = '{}/kw/instagram/webhook/{}'.format(
            burl, instagram_webhook_token)
        self.write({
            'instagram_webhook_token': instagram_webhook_token,
            'instagram_copy_url': webhook_url,
            'instagram_verify_token':
                self.generate_verify_token(), })
