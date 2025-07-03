{
    'name': 'Chatbot statistics',
    'version': '17.0.2.0.1',
    'license': 'OPL-1',
    'category': 'Extra Tools',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'depends': [
        'kw_chatbot',
        'kw_chatbot_builder',
    ],

    'data': [
        'security/ir.model.access.csv',

        'views/menu_views.xml',
        'views/conversation_category_views.xml',
        'views/operator_activity_views.xml',

        'wizard/statistics_wizard_set_category.xml',
    ],

    'images': [
        'static/description/icon.png',
    ],

    'installable': True,
}
