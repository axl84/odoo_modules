/** @odoo-module */
console.log('Rendered: kw_checkbox_pos.EditExciseInput');

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class EditExciseInput extends Component {
    static template = "EditExciseInput";

    onKeyup(event) {
        if (event.key === "Enter" && event.target.value.trim() !== "") {
            this.props.createNewItem();
        }
    }
    onInput(event) {
        this.props.onInputChange(this.props.item._id, event.target.value);
    }
}
registry.category("pos_screens").add("EditExciseInput", EditExciseInput);
