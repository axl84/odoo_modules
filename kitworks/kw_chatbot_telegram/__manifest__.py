{
    'name': 'Chatbot Telegram',
    'version': '17.0.2.0.11',
    'license': 'OPL-1',
    'category': 'Extra Tools',
    'summary': 'Adds Telegram connector an Telegram specific functionality',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'depends': [
        'kw_chatbot', 'crm'
    ],
    'external_dependencies': {
        'python': [
            'telebot',
        ],
    },
    'data': [
        'data/sender.xml',

        'views/notifications_views.xml',
        'views/chat_views.xml',
        'views/sender_views.xml',

    ],
    'installable': True,
    'images': [
        'static/description/cover.png',
        'static/description/icon.png',
    ],
    'price': 100,
    'currency': 'EUR',
}
