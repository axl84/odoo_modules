{
    'name': 'Chatbot WhatsApp builder',
    'version': '17.0.1.0.8',
    'license': 'OPL-1',
    'category': 'Extra Tools',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'depends': [
        'kw_chatbot_builder', 'kw_chatbot_whatsapp',
    ],

    'data': [
        'security/ir.model.access.csv',

        'views/step_views.xml',
    ],

    'installable': True,
}
