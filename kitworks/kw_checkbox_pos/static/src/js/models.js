/** @odoo-module */
console.log('Rendered: kw_checkbox_pos.models');

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async checkbox_qr(pos_reference) {
        if ($('.checkbox_qr').length == 0) {
            const domain = [['pos_reference', 'like', pos_reference]];
            const data = await this.orm.call('pos.order', "search_read", [domain]);
            if (data.length > 0 && data[0].checkbox_qr && !this.config.kw_is_checkbox_check_in_pos) {
                $('.pos-receipt').append(
                    `<div class="checkbox_qr" style="width:100%;display:flex;justify-content: center;">
                        <img style="width:130px" src="data:image/png;base64,${data[0].checkbox_qr}">
                    </div>`
                );
            } else if (data.length > 0 && data[0].kw_checkbox_receipt_id && this.config.kw_is_checkbox_check_in_pos) {
                const domain_che = [['id', '=', data[0].kw_checkbox_receipt_id[0]]];
                const data_check = await this.orm.call('kw.checkbox.receipt', "search_read", [domain_che]);
                if (data_check.length > 0 && data_check[0].text) {
                    $('.pos-receipt').html(data_check[0].text);
                }
            }
        }
        return false;
    },
});
