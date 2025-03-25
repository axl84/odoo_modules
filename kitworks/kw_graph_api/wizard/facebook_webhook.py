import logging

from odoo import fields, models, _
from ..models.graph_api import FacebookGraphApi

_logger = logging.getLogger(__name__)


class FacebookWebhookWizard(models.TransientModel):
    _name = 'facebook.webhook.wizard'
    _description = 'facebook.webhook.wizard'

    facebook_app_id = fields.Many2one(
        comodel_name='kw.facebook.app', required=True, readonly=True, )
    facebook_object = fields.Char(
        required=True, readonly=True, )
    facebook_fields = fields.Char(
        required=True, readonly=True, )
    callback_url = fields.Char(
        required=True, readonly=True, )
    verify_token = fields.Char(
        required=True, readonly=True, )

    def facebook_webhook_fields(self):
        body = {
            'access_token': self.facebook_app_id.facebook_app_access_token,
            'object': self.facebook_object,
            'fields': self.facebook_fields,
            'callback_url': self.callback_url,
            'verify_token': self.verify_token, }
        return body

    def facebook_update_webhook(self):
        body = self.facebook_webhook_fields()
        app_data = FacebookGraphApi().post_facebook_graph(
            url='/v14.0/app/subscriptions', body=body)
        if app_data.get('data'):
            mess = 'The webhook has been updated'
        else:
            mess = app_data.get('error')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Update Facebook Webhook! Result: {}').format(
                    mess),
                'next': {'type': 'ir.actions.act_window_close'}, }}
