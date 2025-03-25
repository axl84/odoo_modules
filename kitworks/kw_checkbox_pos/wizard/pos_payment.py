import logging

from odoo import models, exceptions, _
from odoo.tools import float_is_zero

_logger = logging.getLogger(__name__)


class PosMakePayment(models.TransientModel):
    _inherit = 'pos.make.payment'

    def check(self):
        self.ensure_one()

        order = self.env['pos.order'].browse(
            self.env.context.get('active_id', False))
        currency = order.currency_id

        init_data = self.read()[0]
        if not float_is_zero(init_data['amount'],
                             precision_rounding=currency.rounding):
            order.add_payment({
                'pos_order_id': order.id,
                'session_id': order.session_id.id,
                'amount': order._get_rounded_amount(init_data['amount']),
                'name': init_data['payment_name'],
                'payment_method_id': init_data['payment_method_id'][0],
            })

        if order._is_pos_order_paid():
            if order.session_id.with_context(
                    **{}).cash_register_balance_end < 0 \
                    and self.payment_method_id.is_cash_count:
                raise exceptions.ValidationError(
                    _("You cannot return more than "
                      "what is available at the box office"))
            order.action_pos_order_paid()
            order._create_order_picking()
            order.checkbox_refund(self)
            return {'type': 'ir.actions.act_window_close'}

        return self.launch_payment()
