{
    'name': 'TurboSMS Viber API',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'category': 'Customizations',
    'license': 'OPL-1',
    'version': '17.0.0.0.2',

    'depends': ['kw_sms_turbosms', ],

    'data': [
        'views/sms_provider.xml',
        'views/sms_sms_views.xml',
        'views/sms_template_views.xml',

        'wizard/sms_composer_views.xml',
    ],

    'installable': True,

    'images': [
        'static/description/cover.png',
        'static/description/icon.png',
    ],

}
