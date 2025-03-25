/** @odoo-module */

console.log('Rendered: kw_checkbox_pos.PaymentScreen');

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
        async validateOrder(isForceValidate) {
            const order = this.currentOrder;
            const data_check = await this.orm.call('pos.session', "check_refund_sum", [, [order.pos_session_id]]);
            let totalCashAmount = 0;
            if (order && order.paymentlines) {
                  totalCashAmount = order.paymentlines.reduce((sum, paymentLine) => {
                    if (paymentLine.payment_method && paymentLine.payment_method.is_cash_count) {
                      sum += paymentLine.amount;
                    }
                    return sum;
                  }, 0);
                }
            if (totalCashAmount < 0 && data_check + totalCashAmount < 0){
                this.popup.add(ErrorPopup, {
                title: _t('You cannot return'),
                body: _t('You cannot return more than what is available at the box office'),
                });
                return;
            }
            super.validateOrder(...arguments);
        },
});
