import logging

from odoo import fields, models
from ..wayforpay.constants import PURCHASE_URL

_logger = logging.getLogger(__name__)


def normalize_float(value):
    return int(value) if float(int(value)) == value else value


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('wayforpay', 'WayForPay')],
        ondelete={'wayforpay': 'set default'})
    wayforpay_merchant_account = fields.Char(
        string='WayForPay Merchant', required_if_provider='wayforpay',
        groups='base.group_user', default='test_merch_n1', )
    wayforpay_merchant_key = fields.Char(
        string='WayForPay Mrechant key', required_if_provider='wayforpay',
        groups='base.group_user', default='flk3409refn54t54t*FNJRET', )
    wayforpay_merchant_domain = fields.Char(
        string='WayForPay Merchant domain', required_if_provider='wayforpay',
        groups='base.group_user', default='localhost', )
    wayforpay_fees = fields.Float(
        string='WayForPay Fees (%)', required_if_provider='wayforpay',
        groups='base.group_user', default=2.5)
    wayforpay_tnx_link = fields.Char(
        help='"Thank you!" page URL after payment confirmation')
    wayforpay_symbols_for_avoid = fields.Text(
        help=("List symbols to remove from product names for WayForPay,"
              "separated by commas (e.g., '\\n,\\t,#,@').")
    )

    def sanitize_product_name(self, name, sanitize_force=False):
        if self.wayforpay_symbols_for_avoid or sanitize_force:
            default = {'\n', '\t', '\r', '\\n', '\\t', '\\r'}
            if self.wayforpay_symbols_for_avoid:
                default.update(
                    set(self.wayforpay_symbols_for_avoid.split(',')))
            for symbol in default:
                name = name.replace(symbol, '')
            name = name.replace('\\', '/').strip()
        return name

    def _wayforpay_get_api_url(self):
        return PURCHASE_URL
