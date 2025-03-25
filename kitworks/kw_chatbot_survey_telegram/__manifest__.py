{
    'name': 'Chatbot Telegram Survey',
    'version': '17.0.2.0.18',
    'license': 'OPL-1',
    'category': 'Extra Tools',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'depends': [
        'kw_chatbot_survey',
        'kw_chatbot_builder_telegram',
        'kw_survey_create_entity',
    ],
    'external_dependencies': {
        'python': [
            'telebot',
        ],
    },
    'data': [
        'views/buttons_views.xml',
    ],
    'installable': True,
}
