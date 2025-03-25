{
    'name': 'TurboSMS API',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'category': 'Marketing',
    'license': 'OPL-1',
    'version': '17.0.0.0.1',

    'depends': ['kw_sms_api', ],
    'data': [
        'security/ir.model.access.csv',

        'views/sms_provider.xml',
        'views/sms_sms_views.xml',

    ],
    'installable': True,

    'images': [
        'static/description/cover.png',
        'static/description/icon.png',
    ],

    'price': 100,
    'currency': 'EUR',
}
