/** @odoo-module */
console.log('Rendered: kw_checkbox_pos.excise_product_screen');

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { Product } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { EditListExcise } from "@kw_checkbox_pos/js/EditListExcise";

patch(ProductScreen.prototype, {
    async clickEvent (e) {
            var kwOrderLine = this.currentOrder.get_orderlines();
            if (kwOrderLine.length && kwOrderLine.active && kwOrderLine[0].product.kw_checkbox_product_category_id) {
                if (kwOrderLine[0].product.kw_checkbox_product_category_id[0] ===
                    event.detail.kw_checkbox_product_category_id[0]) {
                    await super.clickEvent(e);
                } else {
                    await this.popup.add(ErrorPopup, {
                    title: _t('This product has another category and cant be added'),
                    body: _t('You should make new receipt for this product'),
                    });
                    return;
                }
            } else {
                await super.clickEvent(e);
            }
        },
});

patch(Product.prototype, {
    async getAddProductOptions(code) {
        const res = await super.getAddProductOptions(code);
        if (this.is_excise_product) {
            let PackExciseLinesOld = [];
            const orderline = this.pos.selectedOrder
                .get_orderlines()
                .filter((line) => !line.get_discount())
                .find((line) => line.product.id === this.id);
            if (orderline && orderline.PackExciseLines) {
                    PackExciseLinesOld = orderline.PackExciseLines.map(item => item.lot_name);
                } else {
                    PackExciseLinesOld = [];
                }
            const product = this;
            const { confirmed, payload } = await this.env.services.popup.add(EditListExcise, {
                title: _t('Input Excise'),
                array_exs: PackExciseLinesOld,
            });
            if (confirmed) {
                const PackExciseLines = payload.newArray
                    .filter(item => !item.id)
                    .map(item => ({ lot_name: item.text }));
                res.PackExciseLines = PackExciseLines;
            } else {
                return;
            }
        }
        return res;
    },
});
