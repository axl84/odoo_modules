{
    'name': 'Chatbot Umnico',
    'version': '17.0.1.0.19',
    'license': 'OPL-1',
    'category': 'Extra Tools',
    'summary': 'Adds Umnico connector '
               'an Umnico specific functionality',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',
    'external_dependencies': {
        'python': [
            'magic',
        ],
    },

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
        'views/conversation_views.xml',
        'wizard/conversation_wizard.xml',

    ],
    'installable': True,
    'images': [
        'static/description/icon.png',
    ],
}
