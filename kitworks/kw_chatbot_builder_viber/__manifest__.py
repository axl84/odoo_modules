{
    'name': 'Chatbot viber builder',
    'version': '17.0.2.0.13',
    'license': 'OPL-1',
    'category': 'Extra Tools',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'depends': [
        'kw_chatbot_builder', 'kw_chatbot_viber',
    ],

    'data': [
        'security/ir.model.access.csv',

        'views/step_views.xml',
        'views/notifications_views.xml',
        'views/buttons_views.xml',
    ],

    'installable': True,
}
