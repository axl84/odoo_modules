odoo.define('kw_chatbot.model.Channel', function (require) {
    "use strict";

    var Channel = require('mail.model.Channel');

    Channel.include({
        _postMessage: function (data) {
            var self = this;
            return this._super.apply(this, arguments, data).then(
                // eslint-disable-next-line no-shadow
                function (data) {
                    self._rpc({
                        model: 'mail.channel',
                        method: 'check_mail_channel',
                        kwargs: {'call_data': data, 'index': self._id},
                    });
                });
        },
    });

    return {
        Channel: Channel,
    };

});
