odoo.define('kw_chatbot.WebsiteLivechatWindow', function (require) {
    "use strict";

    var session = require('web.session');
    var LivechatWindow =
        require('im_livechat.legacy.im_livechat.WebsiteLivechatWindow');

    LivechatWindow.include({
        events: _.extend({
            'click .js_chatbot_button_handle': '_handleButton',
        }, LivechatWindow.prototype.events),
        _handleButton: function (event) {
            var callbackData =
                event.currentTarget.attributes['callback-value'].nodeValue;
            session.rpc('/im_livechat_bot/handle/call',
                {'callback_data': {'body': callbackData},
                    'uuid': this._thread._uuid});
        },
        _postMessage: function (messageData) {
            this._super.apply(this, arguments);
            this.trigger_up('handle_message_chat_window',
                {messageData: messageData});
        },
    });
});
