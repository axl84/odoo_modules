odoo.define('kw_chatbot.model.Message', function (require) {
    "use strict";

    var Message = require('mail.model.Message');

    Message.include({
        _setInitialData: function (data) {
            this._button = data.button;
            return this._super(data);
        },
        addButton: function () {
            return this._button;
        },
    });
    return {
        Message: Message,
    };
});
