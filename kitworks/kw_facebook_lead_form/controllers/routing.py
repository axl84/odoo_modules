import logging

from odoo.http import request
from odoo.addons.kw_graph_api.controllers.routing import FacebookWebhookRouting

_logger = logging.getLogger(__name__)


class LeadgenFacebookWebhookRouting(FacebookWebhookRouting):

    def facebook_page_handler(self, page_id, data, httprequest, webhook_token):
        res = super(LeadgenFacebookWebhookRouting, self).facebook_page_handler(
            page_id, data, httprequest, webhook_token)
        for event in data:
            if event.get('changes'):
                for changes in event.get('changes'):
                    if changes.get('field') == 'leadgen':
                        facebook_page = request.env['kw.facebook.page']
                        page = facebook_page.sudo().search([
                            ('id', '=', page_id.id),
                            ('active', '=', True),
                            ('is_facebook_webhook', '=', True),
                            ('is_lead_form', '=', True),
                            ('page_id', '=', data[0].get('id')), ],
                            limit=1)
                        if page:
                            page.facebook_form_lead_process_call(
                                changes.get('value'))
        return res
