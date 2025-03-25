odoo.define('kw_chatbot.model.ThreadWidget', function (require) {
    "use strict";

    var ThreadWidget = require('mail.widget.Thread');

    ThreadWidget.include({
        events: _.extend({}, ThreadWidget.prototype.events, {
            'click .js_chatbot_button_handle': '_handleButton',
        }),
        _handleButton: function (event) {
            var callbackData =
                event.currentTarget.attributes['callback-value'].nodeValue;
            var channelIndex =
                event.currentTarget.attributes['channel-index'].nodeValue;
            this._rpc({
                model: 'mail.channel',
                method: 'check_mail_channel',
                kwargs:
                    {'callback_data': {'body': callbackData},
                        'index': channelIndex},
            });
        },
    });
});
