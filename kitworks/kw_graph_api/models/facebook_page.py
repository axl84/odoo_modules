import hashlib
import logging
import os

from odoo import models, fields, api
from .graph_api import FacebookGraphApi

_logger = logging.getLogger(__name__)


class FacebookPage(models.Model):
    _name = 'kw.facebook.page'
    _description = 'Facebook Page'

    def _default_get(self, vals):
        params = self.env['ir.config_parameter'].sudo().get_param(
            vals) or False
        if params:
            if all(x.isdigit() for x in params.split()):
                return int(params)
        return params

    name = fields.Char(
        string='App Name', )
    active = fields.Boolean(
        default=True, )
    facebook_app_id = fields.Many2one(
        comodel_name='kw.facebook.app',
        required=True, ondelete='cascade', )

    access_token = fields.Char(
        required=True, )
    page_id = fields.Char(
        required=True, string='Page ID')
    is_developer_mode = fields.Boolean(
        default=False, )
    net_object = fields.Selection(
        selection=[('page', 'Facebook (Page)'), ('instagram', 'Instagram')],
        default='page', required=True, string='Object')
    is_facebook_webhook = fields.Boolean(
        related='facebook_app_id.is_facebook_webhook', )
    page_webhook_token = fields.Char(
        related='facebook_app_id.page_webhook_token', )
    instagram_webhook_token = fields.Char(
        related='facebook_app_id.instagram_webhook_token', )
    subscribe_msg = fields.Char(
        default='Subscribe or unsubscribe for new '
                'permissions for correct work', )

    # crm.lead
    crm_user_id = fields.Many2one(
        comodel_name='res.users', string='Salesperson')
    crm_team_id = fields.Many2one(
        comodel_name='crm.team', string='Sales Team')
    crm_type = fields.Selection([
        ('lead', 'Lead'), ('opportunity', 'Opportunity')],
        default='opportunity', string='Type')
    crm_medium_id = fields.Many2one(
        comodel_name='utm.medium', string='Medium', )
    crm_source_id = fields.Many2one(
        comodel_name='utm.source', string='Source', )
    crm_name_prefix = fields.Char(
        string='Name Prefix', default='Facebook')

    _sql_constraints = [
        ("name_page_id", "unique (page_id)",
         "This page has already been added!"), ]

    def update_crm_lead_data(self, data):
        crm_data = data.update({
            "user_id": self.crm_user_id.id if self.crm_user_id else False,
            "team_id": self.crm_team_id.id if self.crm_team_id else False,
            "medium_id":
                self.crm_medium_id.id if self.crm_medium_id else False,
            "type": self.crm_type,
            "source_id":
                self.crm_source_id.id if self.crm_source_id else False, })
        return crm_data

    def _get_facebook_long_lived_token(self):
        survey_form = self.env['kw.facebook.page'].sudo().search([
            ('active', '=', True), ])
        if survey_form:
            for form in survey_form:
                form.get_facebook_long_lived_token()

    def get_facebook_long_lived_token(self):
        params = {
            'grant_type': 'fb_exchange_token',
            'client_id': self.facebook_app_id.app_id,
            'client_secret': self.facebook_app_id.facebook_app_secret,
            'fb_exchange_token': self.access_token}
        res = FacebookGraphApi().get_facebook_graph(
            url='/oauth/access_token', params=params)
        if res.get('data'):
            token = res['data'].get('access_token')
            if token:
                self.write({'access_token': token})
        else:
            raise ValueError('Failed to get long-term token!{}'.format(
                res.get('error')))

    @api.model
    def generate_verify_token(self):
        r_bytes = os.urandom(16)
        return str(hashlib.sha256(r_bytes).hexdigest())

    def get_permission(self):
        per = self.facebook_app_id.get_permission(self.net_object)
        return per

    def resubscribe_page(self):
        facebook_sdk_token = self.generate_verify_token()
        permission = self.get_permission()
        return {
            'type': 'ir.actions.act_url',
            'name': "Facebook Login",
            'target': '_blank',
            'url': '/kw/facebook/login/%s/%s/%s?permission=%s' % (
                self.facebook_app_id.id, self.net_object,
                facebook_sdk_token, permission)}
