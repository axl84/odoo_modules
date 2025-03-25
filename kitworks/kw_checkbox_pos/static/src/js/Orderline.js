/** @odoo-module */
console.log('Rendered: kw_checkbox_pos.ExciseOrderline');


import { Orderline } from "@point_of_sale/app/store/models";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { EditListExcise } from "@kw_checkbox_pos/js/EditListExcise";

patch(Orderline.prototype, {
    async editPackExciseLines() {
        const orderline = this;
        const product = orderline.get_product();
        let PackExciseLinesOld = [];
        if (orderline && orderline.PackExciseLines) {
            PackExciseLinesOld = orderline.PackExciseLines.map(item => item.lot_name);
        } else {
            PackExciseLinesOld = [];
        }
        const { confirmed, payload } = await this.env.services.popup.add(EditListExcise, {
                title: _t('Input Excise'),
                array_exs: PackExciseLinesOld,
            });
        if (confirmed) {
            const PackExciseLinesNew = payload.newArray
                .filter(item => !item.id)
                .map(item => ({ lot_name: item.text }));
            orderline.PackExciseLines = PackExciseLinesNew;
            if (orderline.refunded_orderline_id) {
                orderline.quantity =  -orderline.PackExciseLines.length;
                orderline.quantityStr = -orderline.PackExciseLines.length;
            }
            else {
                orderline.quantity =  orderline.PackExciseLines.length;
                orderline.quantityStr = orderline.PackExciseLines.length;
            }
        } else {
            return;
        }
    },
    getDisplayData() {
        let originalData = super.getDisplayData(...arguments);
        originalData.is_excise_product = this.get_product().is_excise_product;
        originalData.excise_barcodes = this.PackExciseLines;
        return originalData;
    },

    export_as_JSON() {
        let originalData_json = super.export_as_JSON(...arguments);
        originalData_json.excise = this.PackExciseLines;
        return originalData_json;
    },
});
