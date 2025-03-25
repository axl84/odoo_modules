import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    kw_facebook_app_access_token = fields.Char(
        string='Facebook App Access Token', )
    kw_facebook_app_secret = fields.Char(
        string='Facebook App Secret',)
    kw_facebook_app_id = fields.Char(
        string='Facebook App ID')

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        params = self.env['ir.config_parameter'].sudo()
        params.set_param(
            'kw_facebook_app_access_token', self.kw_facebook_app_access_token)
        params.set_param(
            'kw_facebook_app_secret', self.kw_facebook_app_secret)
        params.set_param(
            'kw_facebook_app_id', self.kw_facebook_app_id)
        return True

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        app_access_token = params.get_param(
            'kw_facebook_app_access_token', False)
        app_secret = params.get_param(
            'kw_facebook_app_secret', False)
        app_id = params.get_param(
            'kw_facebook_app_id', False)
        res.update(
            kw_facebook_app_access_token=app_access_token,
            kw_facebook_app_secret=app_secret,
            kw_facebook_app_id=app_id)
        return res
