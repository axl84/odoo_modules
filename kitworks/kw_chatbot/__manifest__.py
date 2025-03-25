{
    'name': 'ChatBot (multiple chat bots in one base)',
    'version': '17.0.2.0.30',
    'license': 'OPL-1',
    'category': 'Extra Tools',
    'summary': 'Create lots of chatbots, customize chat flow, '
               'connect to multiple messengers, '
               'integrate with odoo objects ',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'depends': ['web', 'base', 'portal', 'im_livechat',
                'kw_mixin', 'kw_phone_search', 'link_tracker', 'resource',
                'generic_mixin', 'sale', 'mail', 'crm'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/notification_cron.xml',
        'data/messenger.xml',
        'data/notification.xml',
        'data/res_users_bot.xml',
        'data/sender.xml',
        'data/default_bots.xml',
        'data/chat.xml',
        'views/mass_send_bot.xml',
        'views/menu_views.xml',
        'views/message_mailing_views.xml',
        'views/messenger_views.xml',
        'views/chat_views.xml',
        'views/users_views.xml',
        'views/sender_views.xml',
        'views/dialog_views.xml',
        'views/conversation_views.xml',
        'views/notification_views.xml',
        'views/crm_lead_views.xml',

        'views/logs_views.xml',
        'views/res_partner_views.xml',
        'wizard/chat_bot_send_views.xml',
        'wizard/chat_bot_partner_send.xml',
        'wizard/chat_bot_settings_views.xml',

    ],
    'assets': {
        'im_livechat.external_lib': [
            # 'kw_chatbot/static/src/js/models/website_livechat_message.js',
            # 'kw_chatbot/static/src/js/website_livechat_window.js',
            # 'kw_chatbot/static/src/js/im_livechat.js',
        ],
        'web.assets_backend': [
            # 'kw_chatbot/static/src/js/models/channel.js',
            # 'kw_chatbot/static/src/js/models/messages/message.js',
            # 'kw_chatbot/static/src/js/thread_widget.js',

            # 'kw_chatbot/static/src/js/kw_chatbot_form_view.js',
            # 'kw_chatbot/static/src/js/kw_chatbot_form_controller.js',
            # 'kw_chatbot/static/src/js/kw_chatbot_step_form_view_dialog.js',
            'kw_chatbot/static/src/js/models/',
            'kw_chatbot/static/src/js/channel_commands.js',
            # 'messaging_initializer/messaging_initializer.js',

        ],
    },
    'installable': True,
    'web.assets_qweb': [
        'kw_chatbot/static/src/xml/thread.xml',
    ],

    'images': [
        'static/description/cover.png',
        'static/description/icon.png',
    ],
    'price': 200,
    'currency': 'EUR',
}
