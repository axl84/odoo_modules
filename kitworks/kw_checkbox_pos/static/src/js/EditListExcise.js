/** @odoo-module */
console.log('Rendered: kw_checkbox_pos.EditListExcise');

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { useAutoFocusToLast } from "@point_of_sale/app/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { useState } from "@odoo/owl";
import { EditExciseInput } from "@kw_checkbox_pos/js/EditExciseInput";
import { registry } from "@web/core/registry";


export class EditListExcise extends AbstractAwaitablePopup {
    static components = { EditExciseInput };
    static template = "EditListExcise";
    static defaultProps = {
        confirmText: _t("Add"),
        cancelText: _t("Discard"),
        array_exs: [],
    };
    setup() {
        super.setup();
        this._id = 0;
        this.state = useState({ array_exs: this._initialize(this.props.array_exs) });
        useAutoFocusToLast();
    }
    _nextId() {
        return this._id++;
    }
    _emptyItem() {
        return {
            text: "",
            _id: this._nextId(),
        };
    }
    _initialize(array_exs) {
        if (array_exs.length === 0) {
            return [this._emptyItem()];
        }
        return array_exs.map((item) =>
            Object.assign(
                {},
                { _id: this._nextId() },
                typeof item === "object" ? item : { text: item }
            )
        );
    }
    _hasMoreThanOneItem() {
        return this.state.array_exs.length > 1;
    }
    removeItem(itemId) {
        this.state.array_exs.splice(
            this.state.array_exs.findIndex((item) => item._id == itemId),
            1
        );
    }
    onInputChange(itemId, text) {
        const item = this.state.array_exs.find((elem) => elem._id === itemId);
        item.text = text;
    }
    createNewItem() {
        if (this.props.isSingleItem) {
            return;
        }
        this.state.array_exs.push(this._emptyItem());
    }
    getPayload() {
        return {
            newArray: this.state.array_exs
                .filter((item) => item.text.trim() !== "")
                .map((item) => Object.assign({}, item)),
        };
    }
}
registry.category("pos_screens").add("EditListExcise", EditListExcise);
