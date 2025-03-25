import logging
import time
import html

from datetime import datetime
from math import ceil
from markupsafe import Markup
from werkzeug import urls
from odoo import fields, models, api
from odoo.exceptions import ValidationError
from ..wayforpay import (
    WayForPay, Form
)


def normalize_float(value):
    return int(value) if float(int(value)) == value else value


def normalize_float_to_int(value):
    return int(value) if float(int(value)) == value else ceil(value)


SUPERUSER_ID = 1

_logger = logging.getLogger(__name__)

WAYFORPAY_STATUSES = {
    'InProcessing': 'draft',
    'WaitingAuthComplete': 'draft',
    'Approved': 'done',
    'Pending': 'pending',
    'Expired': 'error',
    'Refunded/Voided': 'cancel',
    'Refunded': 'cancel',
    'Declined': 'cancel',
    'RefundInProcessing': 'cancel',
}


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    kw_wfp_response = fields.Text(
        string='WfP status response')

    kw_fees = fields.Float()

    @api.model
    def _get_tx_from_notification_data(self, provider, data):
        tx = super()._get_tx_from_notification_data(provider, data)
        if provider != 'wayforpay':
            return tx

        reference = data.get('orderReference')
        # _logger.info('reference')
        # _logger.info(reference)
        time.sleep(0.5)
        if not reference:
            error_msg = 'WayForPay: received data with missing ' \
                        'reference (%s)' % reference
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        txs = self.env['payment.transaction'].search(
            [('reference', 'ilike', reference)], limit=1)
        # _logger.info('@ @ @ txs')
        # _logger.info(txs)
        if not txs or len(txs) > 1:
            error_msg = 'WayForPay: received data for reference %s' % reference
            if not txs:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        return txs[0]

    # pylint: disable=R1710
    def _process_notification_data(self, data):
        super()._process_notification_data(data)
        if self.provider_code != 'wayforpay':
            return

        self.kw_wfp_response = data
        state = data.get('transactionStatus')
        state_message = data.get('reason')
        res = {'provider_reference': data.get('authCode'),
               'state_message': state_message,
               'state': WAYFORPAY_STATUSES.get(state),
               'last_state_change': fields.Datetime.now(),
               'kw_wfp_response': data, }
        fees = data.get('fee')
        if fees:
            res['kw_fees'] = fees
        is_done = self.state == 'done'
        result = self.update(res)
        if not is_done and res['state'] == 'done':
            self._set_done(state_message)
            self.with_user(SUPERUSER_ID)._finalize_post_processing()
        if res['state'] == 'cancel':
            self._set_canceled(state_message)
        if res['state'] == 'error':
            self._set_error(state_message)
        return result

    def check_status_wayforpay(self):
        for obj in self:
            wfp = WayForPay(obj.provider_id.wayforpay_merchant_account,
                            obj.provider_id.wayforpay_merchant_key)
            wfp_response = wfp.api.check_status({
                'orderReference': obj.reference,
                'apiVersion': 1, })
            obj._process_notification_data(wfp_response)

    def _get_processing_values(self):
        """ Override of `_get_processing_values()` to unescape created form.

        :param self: Self@PaymentTransaction
        :return: updated processing_values.
        :rtype: `processing_values` dict.
        """
        processing_values = super()._get_processing_values()
        if self.provider_code != 'wayforpay':
            return processing_values

        processing_values['redirect_form_html'] = \
            Markup(html.unescape(processing_values['redirect_form_html']))
        return processing_values

    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'wayforpay':
            return res

        wayforpay_tx_values = dict(processing_values)
        provider = self.provider_id
        base_url = provider.get_base_url()
        tx = self.env['payment.transaction'].search(
            [('reference', '=', processing_values['reference'])], limit=1)
        currency_id = self.env['res.currency'].search(
            [('id', '=', processing_values['currency_id'])])

        # pylint: disable=W0101
        form = False
        if tx and hasattr(tx, 'sale_order_ids') \
                and tx.sale_order_ids and provider:
            product_name_list = [
                provider.sanitize_product_name(x.product_id.name,
                                               sanitize_force=True)
                for x in tx.sale_order_ids.order_line
            ]
            form = Form(
                merchant_account=provider.wayforpay_merchant_account,
                merchant_key=provider.wayforpay_merchant_key,
                params=dict(
                    merchantDomainName=provider.wayforpay_merchant_domain,
                    serviceUrl=urls.url_join(
                        base_url, '/payment/wayforpay/service/'),
                    returnUrl=urls.url_join(
                        base_url, provider.wayforpay_tnx_link
                        or '/payment/wayforpay/return/'),
                    merchantTransactionSecureType='AUTO',
                    apiVersion=1,
                    orderReference=processing_values['reference'],
                    orderDate=int(tx.sale_order_ids.date_order.timestamp()),
                    amount=normalize_float(processing_values['amount']),
                    currency=currency_id.name,
                    productName=product_name_list,
                    productCount=[normalize_float_to_int(x.product_uom_qty)
                                  for x in tx.sale_order_ids.order_line],
                    productPrice=[normalize_float(x.price_unit)
                                  for x in tx.sale_order_ids.order_line], ))
        elif tx and hasattr(tx, 'invoice_ids') and \
                tx.invoice_ids and provider:
            product_name_list = [
                provider.sanitize_product_name(x.product_id.name,
                                               sanitize_force=True)
                for x in tx.invoice_ids.invoice_line_ids
            ]
            form = Form(
                merchant_account=provider.wayforpay_merchant_account,
                merchant_key=provider.wayforpay_merchant_key,
                params=dict(
                    merchantDomainName=provider.wayforpay_merchant_domain,
                    serviceUrl=urls.url_join(
                        base_url, '/payment/wayforpay/service/'),
                    returnUrl=urls.url_join(
                        base_url, provider.wayforpay_tnx_link
                        or '/payment/wayforpay/return/'),
                    merchantTransactionSecureType='AUTO',
                    apiVersion=1,
                    orderReference=processing_values['reference'],
                    orderDate=int(datetime.combine(
                        tx.invoice_ids.invoice_date,
                        datetime.min.time()).timestamp()),
                    amount=normalize_float(processing_values['amount']),
                    currency=currency_id.name,
                    productName=product_name_list,
                    productCount=[normalize_float_to_int(x.quantity)
                                  for x in tx.invoice_ids.invoice_line_ids],
                    productPrice=[normalize_float(x.price_unit) for x in
                                  tx.invoice_ids.invoice_line_ids], ))
        elif tx and provider:
            form = Form(
                merchant_account=provider.wayforpay_merchant_account,
                merchant_key=provider.wayforpay_merchant_key,
                params=dict(
                    merchantDomainName=provider.wayforpay_merchant_domain,
                    serviceUrl=urls.url_join(
                        base_url, '/payment/wayforpay/service/'),
                    returnUrl=urls.url_join(
                        base_url, provider.wayforpay_tnx_link
                        or '/payment/wayforpay/return/'),
                    merchantTransactionSecureType='AUTO',
                    apiVersion=1,
                    orderReference=processing_values['reference'],
                    orderDate=tx.create_date.timestamp(),
                    amount=normalize_float(processing_values['amount']),
                    currency=currency_id.name, ))
        if form:
            wayforpay_tx_values.update({'wayforpay_inputs': form.get_inputs()})
            wayforpay_tx_values.update(
                {'api_url': provider._wayforpay_get_api_url()})
        return wayforpay_tx_values
