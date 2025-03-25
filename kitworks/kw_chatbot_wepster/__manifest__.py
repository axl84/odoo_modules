{
    'name': 'Chatbot Wepster',
    'version': '17.0.1.0.16',
    'license': 'OPL-1',
    'category': 'Extra Tools',
    'summary': 'Adds Wepster connector '
               'an Wepster specific functionality',

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
        'views/res_partner_views.xml',

        'wizard/conversation_wizard.xml',
    ],
    'installable': True,
    'images': [
        'static/description/icon.png',
    ],
}
