/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onWillUnmount } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class NoReplyConversation extends Component {
    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.state = useState({ count: 0 });

        onWillStart(async () => {
            await this.fetchConversationCount();
            this.startConversationCountUpdate();
        });

        onWillUnmount(() => {
            this.stopConversationCountUpdate();
        });
    }

    // Get Count
    async fetchConversationCount() {
        try {
            const count = await this.orm.call("kw.chatbot.conversation", "search_count", [[['is_no_reply', '=', true]]]);
            this.state.count = count;
        } catch (error) {
            console.error("Error fetching conversation count:", error);
        }
    }

    // Timer
    startConversationCountUpdate() {
        this.intervalId = setInterval(async () => {
            await this.fetchConversationCount();
        }, 120000); // 2 min
    }

    // Clear
    stopConversationCountUpdate() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
        }
    }

    // Tree View
    openConversationViews() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "kw.chatbot.conversation",
            views: [
                [false, "tree"],
                [false, "form"],
            ],
            target: "current",
            domain: [['is_no_reply', '=', true]],
            name: _t("No Reply"),
        });
    }
}

NoReplyConversation.template = "web.NoReplyConversation";

export const systrayRefreshItem = {
    Component: NoReplyConversation,
};
registry.category("systray").add("web.no_reply_conversation_button", systrayRefreshItem);
