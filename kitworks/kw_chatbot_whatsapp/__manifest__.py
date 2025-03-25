{
    'name': 'Chatbot WhatsApp',
    'version': '17.0.1.0.4',
    'license': 'OPL-1',
    'category': 'Extra Tools',
    'summary': 'Adds WhatsApp connector '
               'an WhatsApp specific functionality',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'depends': [
        'kw_chatbot', 'kw_graph_api',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_long_token.xml',
        'data/sender.xml',
        'views/chat_views.xml',
        'views/sender_views.xml',
        'views/template_views.xml',

        'wizard/send_wa_template_views.xml',
    ],
    'installable': True,
    'images': [
        'static/description/icon.png',
    ],
}
