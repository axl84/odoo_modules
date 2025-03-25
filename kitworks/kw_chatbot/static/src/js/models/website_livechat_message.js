odoo.define('kw_chatbot.model.WebsiteLivechatMessage', function (require) {
    "use strict";

    var WebsiteLivechatMessage =
        require('im_livechat.legacy.im_livechat.model.WebsiteLivechatMessage');

    WebsiteLivechatMessage.include({
        init: function (parent, data, options) {
            this._button = data.button;
            this._super.apply(this, arguments, options);
        },
        addButton: function () {
            return this._button;
        },
    });
});
