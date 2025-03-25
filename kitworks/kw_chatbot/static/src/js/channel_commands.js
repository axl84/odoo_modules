/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

registry.category("discuss.channel_commands").add("end", {
    help: _t("End this conversation"),
    methodName: "execute_command_end",
});
