{
    'name': 'SMS API',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'category': 'Marketing',
    'license': 'OPL-1',
    'version': '17.0.1.1.11',

    'depends': ['sms', ],
    'data': [
        'security/ir.model.access.csv',
        'data/sms_provider.xml',
        'data/cron.xml',

        'views/sms_log.xml',
        'views/sms_sms_views.xml',
        'views/sms_provider.xml',

        'wizard/sms_composer_views.xml',
        'views/res_partner_views.xml',

    ],
    'installable': True,

    'images': [
        'static/description/cover.png',
        'static/description/icon.png',
    ],
    'assets': {
        'web.assets_common': [
            'kw_sms_api/static/src/components/*/*', ],
    },
}
