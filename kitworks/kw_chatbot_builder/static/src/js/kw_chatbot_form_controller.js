/** @odoo-module **/

import { _t } from 'web.core';
import FormController from 'web.FormController';
import ChatbotStepFormViewDialog from 'kw_chatbot_builder.ChatbotStepFormViewDialog';

const ChatbotFormController = FormController.extend({
    custom_events: Object.assign({}, FormController.prototype.custom_events, {
        chatbot_save_form: '_chatbotSaveForm',
        chatbot_add_step: '_chatbotAddStep',
    }),

    async _chatbotSaveForm(ev) {
        await this.saveRecord(this.handle, {
            stayInEdit: true,
        });

        if (ev && ev.data.callback) {
            ev.data.callback();
        }

        const state = this.model.get(this.handle);
        this.renderer.confirmChange(state, state.id, ['chatbot_step_ids']);
    },

    async _chatbotAddStep(ev) {
        this.$('.o_field_one2many[name="chatbot_step_ids"] .o_field_x2many_list_row_add a').click();
        if (ev && ev.data.callback) {
            ev.data.callback();
        }
    },

    async _onOpenOne2ManyRecord(ev) {
        ev.stopPropagation();
        const data = ev.data;

        if (data.field.relation !== "kw.chatbot.step") {
            return this._super(...arguments);
        }

        const record = data.id ? this.model.get(data.id, {raw: true}) : null;

        // Sync with the mutex to wait for potential onchanges
        await this.model.mutex.getUnlockedDef();

        new ChatbotStepFormViewDialog(this, {
            context: data.context,
            domain: data.domain,
            fields_view: data.fields_view,
            model: this.model,
            on_saved: data.on_saved,
            on_remove: data.on_remove,
            parentID: data.parentID,
            readonly: data.readonly,
            editable: data.editable,
            deletable: record ? data.deletable : false,
            disable_multiple_selection: true,
            recordID: record && record.id,
            res_id: record && record.res_id,
            res_model: data.field.relation,
            shouldSaveLocally: true,
            title: (record ? _t("Open: ") : _t("Create ")) + (ev.target.string || data.field.string),
        }).open();
    },

});

export default ChatbotFormController;
