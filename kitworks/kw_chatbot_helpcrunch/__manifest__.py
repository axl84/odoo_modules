{
    'name': 'Chatbot HelpCrunch',
    'version': '17.0.2.0.4',
    'license': 'OPL-1',
    'category': 'Extra Tools',
    'summary': 'Adds HelpCrunch connector '
               'an HelpCrunch specific functionality',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'depends': [
        'kw_chatbot',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sender.xml',

        'views/chat_views.xml',
        'views/sender_views.xml',
        'views/messenger_views.xml',
    ],
    'installable': True,
    'images': [
        'static/description/icon.png',
    ],
    'price': 100,
    'currency': 'EUR',
}
