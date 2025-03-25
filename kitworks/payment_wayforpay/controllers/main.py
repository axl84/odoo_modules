import json
import logging
import pprint
from datetime import datetime

import werkzeug
from odoo import http
from odoo.http import request
from ..wayforpay.utils import generate_signature

_logger = logging.getLogger(__name__)


class WayForPayController(http.Controller):
    _return_url = '/payment/wayforpay/return'
    _service_url = '/payment/wayforpay/service'

    @http.route(type='http', auth='none', csrf=False,
                methods=['GET', 'POST'], route=[_return_url, ],
                save_session=False, )
    def wayforpay_return_from_redirect(self, **post):
        _logger.info(f'WayForPay return \n\n\n{post}')
        wayforpay_draft_tx = request.env['payment.transaction'].sudo().search([
            ('state', '=', 'draft'),
            ('provider_code', '=', 'wayforpay'),
        ])
        wayforpay_draft_tx.check_status_wayforpay()
        return werkzeug.utils.redirect('/payment/status')

    @http.route(type='http', auth='none', csrf=False, route=[
        _service_url, ], methods=['GET', 'POST'], )
    def wayforpay_service(self, **post):
        _logger.info('WayForPay: entering form_feedback with post data %s',
                     pprint.pformat(post))  # debug
        post = json.loads(next(iter(post)))
        tx = request.env['payment.transaction'].sudo()\
            ._handle_notification_data('wayforpay', post)
        cur_time = int(datetime.now().timestamp())
        return json.dumps({
            'orderReference': post.get('orderReference'),
            'status': 'accept',
            'time': cur_time,
            'signature': generate_signature(
                tx.sudo().provider_id.wayforpay_merchant_key, [
                    post.get('orderReference'), 'accept', cur_time, ]), })
