odoo.define('kw_chatbot.im_livechat', function (require) {
    "use strict";

    require('bus.BusService');
    var core = require('web.core');
    var session = require('web.session');
    var LivechatButton =
        require('im_livechat.legacy.im_livechat.im_livechat').LivechatButton;
    var QWeb = core.qweb;

    LivechatButton.include({
        custom_events: _.extend({}, LivechatButton.prototype.custom_events, {
            'handle_message_chat_window': '_onHandleMessageChatWindow',
        }),
        _onHandleMessageChatWindow: function (ev) {
            session.rpc('/im_livechat_bot/handle/call',
                {'call_data': {'body': ev.data.messageData.content},
                    'uuid': this._livechat.getUUID()});
        },
        _loadQWebTemplate: function () {
            return session.rpc('/im_livechat_bot/load_templates').then(
                function (templates) {
                    _.each(templates, function (template) {
                        QWeb.add_template(template);
                    });
                });
        },
    });
    return {
        LivechatButton: LivechatButton,
    };

});
