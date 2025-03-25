/** @odoo-module **/

import { SendSMSButton } from "@sms/components/sms_button/sms_button";

import { patch } from "@web/core/utils/patch";

patch(SendSMSButton.prototype, "kw_sms_api_sms_button", {
  async onClick() {
        await this.props.record.save();
        this.action.doAction({
            type: "ir.actions.act_window",
            target: "new",
            name: this.title,
            res_model: "sms.composer",
            views: [[false, "form"]],
            context: {
                ...this.user.context,
                default_res_model: this.props.record.resModel,
                default_res_id: this.props.record.resId,
                default_number_field_name: this.props.name,
                default_composition_mode: 'mass',
                default_mass_keep_log: true,
            }
        }, {
            onClose: () => {
                this.props.record.load();
                this.props.record.model.notify();
            },
        });
    }
});
