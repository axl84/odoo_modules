{
    'name': 'Chatbot instagram',
    'version': '17.0.1.0.4',
    'license': 'OPL-1',
    'category': 'Extra Tools',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'depends': [
        'kw_chatbot', 'kw_graph_api',
    ],
    'external_dependencies': {
        'python': [
            'pymessenger',
        ],
    },
    'data': [
        'data/sender.xml',

        'views/chat_views.xml',
        'views/sender_views.xml',
        'views/messenger_views.xml',
    ],
    'installable': True,
    'images': [
        'static/description/cover.png',
        'static/description/icon.png',
    ],
    'price': 500,
    'currency': 'EUR',
}
