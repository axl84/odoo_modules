{
    'name': 'Chatbot Facebook Lead Form (Survey)',
    'version': '17.0.1.0.7',
    'license': 'OPL-1',
    'category': 'Extra Tools',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'depends': [
        'kw_graph_api', 'kw_survey_create_lead',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/facebook_page_view.xml',
        'views/survey_view.xml',
        'data/ir_cron_lead.xml',
    ],
    'installable': True,

    'price': 100,
    'currency': 'EUR',
}
