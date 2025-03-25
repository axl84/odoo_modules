{
    'name': 'Chatbot telegram builder sale',
    'version': '17.0.2.0.4',
    'license': 'OPL-1',
    'category': 'Extra Tools',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'depends': [
        'kw_chatbot_builder_sale', 'kw_chatbot_builder_telegram'
    ],

    'external_dependencies': {
        'python': [
            'telebot',
        ],
    },

    'data': [
        'views/step_views.xml',
        'views/buttons_views.xml',
        'wizard/payment_link_wizard_view.xml',
    ],

    'installable': True,
}
