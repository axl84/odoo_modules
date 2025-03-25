{
    'name': 'Chatbot Odoo Survey',
    'version': '17.0.2.0.11',
    'license': 'OPL-1',
    'category': 'Extra Tools',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'depends': [
        'kw_chatbot_builder', 'survey',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/step_views.xml',
        'views/survey_views.xml',
    ],
    'installable': True,
}
