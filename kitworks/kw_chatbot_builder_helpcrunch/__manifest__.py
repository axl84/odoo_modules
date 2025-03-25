{
    'name': 'Chatbot Helpcrunch builder',
    'version': '17.0.2.0.6',
    'license': 'OPL-1',
    'category': 'Extra Tools',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'depends': [
        'kw_chatbot_builder', 'kw_chatbot_helpcrunch',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/messenger_views.xml',
    ],
    'installable': True,
}
