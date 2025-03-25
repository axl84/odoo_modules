/** @odoo-module **/
console.log('Rendered: kw_checkbox_pos.receipt_screen.js');


import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { ReprintReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/reprint_receipt_screen";
import {Component, xml, markup} from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { ReceiptHeader } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt_header/receipt_header";
import { omit } from "@web/core/utils/objects";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";

export class CheckboxCheckImage extends Component {
    static defaultProps = {
        class: "",
    };
    static components = {
        Orderline,
        OrderWidget,
        ReceiptHeader,
    };
    static props = {
        data: Object,
        formatCurrency: Function,
    };
    omit(...args) {
        return omit(...args);
    }
    static template = xml`
        <div class="pos-receipt" >
             <t t-out="props.data.data_html_content"/>
        </div>
    `;
}

patch(ReceiptScreen.prototype, {
    async printReceipt() {
        const domain = [['pos_reference', 'like', this.pos.get_order().name]];
        const data_order = await this.orm.call('pos.order', "search_read", [domain]);
        if (data_order.length > 0 && data_order[0].checkbox_qr && !this.pos.config.kw_is_checkbox_check_in_pos) {
            this.buttonPrintReceipt.el.className = "fa fa-fw fa-spin fa-circle-o-notch";
            const export_for_printing_data = this.pos.get_order().export_for_printing();
            export_for_printing_data.pos_qr_code_checkbox = `/checkbox/QR/${data_order[0].id}`;
            const isPrinted = await this.printer.print(
                OrderReceipt,
                {
                    data: export_for_printing_data,
                    formatCurrency: this.env.utils.formatCurrency,
                },
                { webPrintFallback: true }
            );
            if (isPrinted) {
                this.currentOrder._printed = true;
                }
            if (this.buttonPrintReceipt.el) {
                this.buttonPrintReceipt.el.className = "fa fa-print";
                }
            return false
        } else if (data_order.length > 0 && data_order[0].kw_checkbox_receipt_id && this.pos.config.kw_is_checkbox_check_in_pos) {
            const domain_che = [['id', '=', data_order[0].kw_checkbox_receipt_id[0]]];
            const data_receipt = await this.orm.call('kw.checkbox.receipt', "search_read", [domain_che]);
            if (data_receipt.length > 0  && data_receipt[0].text) {
                this.buttonPrintReceipt.el.className = "fa fa-fw fa-spin fa-circle-o-notch";
                const isPrinted = await this.printer.print(
                    CheckboxCheckImage,
                    {
                        data: {'data_html_content': markup(data_receipt[0].text)},
                        formatCurrency: this.env.utils.formatCurrency,
                    },
                    { webPrintFallback: true }
                );
                if (isPrinted) {
                    this.currentOrder._printed = true;
                    }
                if (this.buttonPrintReceipt.el) {
                    this.buttonPrintReceipt.el.className = "fa fa-print";
                    }
                return false
                }
        }
        super.printReceipt();
    },

});

patch(ReprintReceiptScreen.prototype, {
    async tryReprint() {
        const domain = [['pos_reference', 'like', this.props.order.name]];
        const data_order = await this.env.services.orm.call('pos.order', "search_read", [domain]);
        if (data_order.length > 0 && data_order[0].checkbox_qr && !this.pos.config.kw_is_checkbox_check_in_pos) {
            this.buttonPrintReceipt.el.className = "fa fa-fw fa-spin fa-circle-o-notch";
            const export_for_printing_data = this.pos.get_order().export_for_printing();
            export_for_printing_data.pos_qr_code_checkbox = `/checkbox/QR/${data_order[0].id}`;
            const isPrinted = await this.printer.print(
                OrderReceipt,
                {
                    data: export_for_printing_data,
                    formatCurrency: this.env.utils.formatCurrency,
                },
                { webPrintFallback: true }
            );
            if (isPrinted) {
                this.currentOrder._printed = true;
                }
            if (this.buttonPrintReceipt.el) {
                this.buttonPrintReceipt.el.className = "fa fa-print";
                }
            return false
        } else if (data_order.length > 0 && data_order[0].kw_checkbox_receipt_id && this.pos.config.kw_is_checkbox_check_in_pos) {
            const domain_che = [['id', '=', data_order[0].kw_checkbox_receipt_id[0]]];
            const data_receipt = await this.env.services.orm.call('kw.checkbox.receipt', "search_read", [domain_che]);
            if (data_receipt.length > 0  && data_receipt[0].text) {
                this.printer.print(
                    CheckboxCheckImage,
                    {
                        data: {'data_html_content': markup(data_receipt[0].text)},
                        formatCurrency: this.env.utils.formatCurrency,
                    },
                    { webPrintFallback: true }
                );
                return false
                }
        }
        super.tryReprint();
    },

});
