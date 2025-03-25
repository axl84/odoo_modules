/** @odoo-module */
console.log('Rendered: kw_checkbox_pos.model');

function isFloatZero(value, precision) {
    const threshold = Math.pow(10, -precision);
    return Math.abs(value) < threshold;
}

import { Orderline, Order } from "@point_of_sale/app/store/models";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";

patch(Order.prototype, {
    async add_product(product, options) {
        super.add_product(product, options);
        if (options.PackExciseLines) {
            this.selected_orderline.quantity = options.PackExciseLines.length;
            this.selected_orderline.quantityStr = options.PackExciseLines.length.toString();
            this.selected_orderline.PackExciseLines = options.PackExciseLines;
        }
    },

    async select_orderline(line) {
        if (line && line.refunded_orderline_id && line.product && line.product.is_excise_product) {
            const PackExciseLinesRef = await this.env.services.orm.call(
            'pos.order.line',
            "get_pack_excise_lines_ref",
            [, [line.refunded_orderline_id]]);

            line.PackExciseLines = PackExciseLinesRef;
        }
        super.select_orderline(line);
    },
    get_rounding_applied() {
        if(this.pos.config.cash_rounding && this.pos.config.kw_is_checkbox_rounding) {
            const only_cash = this.pos.config.only_round_cash_method;
            const paymentlines = this.get_paymentlines();
            const last_line = paymentlines ? paymentlines[paymentlines.length-1]: false;
            const last_line_is_cash = last_line ? last_line.payment_method.is_cash_count == true: false;
            if (!only_cash || (only_cash && last_line_is_cash)) {
                var remaining = this.get_total_with_tax();
                var total;
                var rounding = this.pos.cash_rounding[0].rounding;
                var decimalPart = remaining % 0.1;
                if (decimalPart < 0) {
                    if (decimalPart <= -0.049) {
                        total = remaining + (-0.1 - decimalPart);
                    } else {
                        total = remaining - decimalPart;
                    }
                }
                else {
                    if (decimalPart >= 0.049) {
                        total = remaining + (0.1 - decimalPart);
                    } else {
                        total = remaining - decimalPart;
                    }
                }


                var sign = remaining > 0 ? 1.0 : -1.0;
                var rounding_applied = total - remaining;
                rounding_applied *= sign;
                if (isFloatZero(rounding_applied, this.pos.currency.decimals)){
                    return 0;
                } else if(Math.abs(this.get_total_with_tax()) < this.pos.cash_rounding[0].rounding) {
                    return 0;
                }
                return sign * rounding_applied;
            }
            else {
                return super.get_rounding_applied();
            }
        }
        return super.get_rounding_applied();;
    },
    async pay() {
        if (this.orderlines.some(line => line.get_product().is_excise_product && line.PackExciseLines && line.PackExciseLines.length !== Math.abs(line.quantity))) {
            const { confirmed } = await this.env.services.popup.add(ConfirmPopup, {
                title: _t("Some Excise Numbers are missing"),
                body: _t("You are trying to sell goods with excise numbers, but some of them are not set.\nContinue anyway?"),
                confirmText: _t("Yes"),
                cancelText: _t("No"),
            });
            if (confirmed) {
                this.pos.mobile_pane = "right";
                this.env.services.pos.showScreen("PaymentScreen");
            }
        }
        else {
            await super.pay();
        }

    },
});
