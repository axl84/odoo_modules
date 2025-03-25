{
    'name': 'Chatbot builder sale',
    'version': '17.0.2.0.3',
    'license': 'OPL-1',
    'category': 'Extra Tools',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'depends': [
        'kw_chatbot_builder',
    ],

    'external_dependencies': {
        'python': [
            'telebot',
        ],
    },

    'data': [
        'views/step_views.xml',
        'views/sale_order_views.xml'
    ],

    'installable': True,
}
