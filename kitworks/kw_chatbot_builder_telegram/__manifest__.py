{
    'name': 'Chatbot telegram builder',
    'version': '17.0.2.0.33',
    'license': 'OPL-1',
    'category': 'Extra Tools',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'depends': [
        'kw_chatbot_builder', 'kw_chatbot_telegram',
        'base_automation', 'sms', 'kw_phone_search',
    ],

    'external_dependencies': {
        'python': [
            'telebot',
        ],
    },

    'data': [
        'security/ir.model.access.csv',

        'views/buttons_views.xml',
        'views/chat_views.xml',
        'views/step_views.xml',
        'views/notifications_buttons_views.xml',
        'views/message_views.xml',
        'views/mass_send_bot.xml',
    ],

    'installable': True,
}
