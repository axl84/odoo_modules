/** @odoo-module alias=kw_chatbot_builder.ChatbotStepFormViewDialog **/

import { _t } from 'web.core';
import FormViewDialog from 'web.view_dialogs';


const ChatbotStepFormViewDialog = FormViewDialog.FormViewDialog.extend({
    init: function (parent, options) {
        this._super(...arguments);

        const readonly = _.isNumber(this.res_id) && this.readonly;
        this.buttons = [{
            text: _t("Save & Close"),
            classes: "btn-primary",
            click: () => {
                this._save().then(() => {
                    parent.trigger_up('chatbot_save_form', {
                        callback: () => {
                            this.close();
                        }
                    });
                });
            },
        }, {
            text: _t("Save & New"),
            classes: "btn-primary",
            click: () => {
                this._save().then(() => {
                    parent.trigger_up('chatbot_save_form', {
                        callback: () => {
                            parent.trigger_up('chatbot_add_step', {
                                callback: () => {this.close();}
                            });
                        }
                    });
                });
            },
        }, {
            text: options.close_text || (readonly ? _t("Close") : _t("Discard")),
            classes: "btn-secondary o_form_button_cancel",
            close: true,
            hotkey: 'j',
            click: () => {
                if (!readonly) {
                    this.form_view.model.discardChanges(this.form_view.handle, {
                        rollback: false,
                    });
                }
            },
        }];
    }
});

export default ChatbotStepFormViewDialog;
