{
    'name': 'Chatbot Viber',
    'version': '17.0.2.0.15',
    'license': 'OPL-1',
    'category': 'Extra Tools',
    'summary': 'Adds Viber connector an Viber specific functionality',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'depends': [
        'kw_chatbot',
    ],
    'external_dependencies': {
        'python': [
            'viberbot',
        ],
    },
    'data': [
        'security/ir.model.access.csv',
        'data/sender.xml',

        'views/buttons_views.xml',
        'views/chat_views.xml',
        'views/sender_views.xml',
        'views/image_button_views.xml',
    ],
    'installable': True,
    'images': [
        'static/description/cover.png',
        'static/description/icon.png',
    ],
    'price': 50,
    'currency': 'EUR',
}
