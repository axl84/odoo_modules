{
    'name': 'Import PrivatBank Autoclient statement',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'category': 'Accounting',
    'license': 'OPL-1',
    'version': '17.0.1.0.15',

    'depends': ['kw_bank_import_base', 'kw_bank_autoclient_privat24_base', ],

    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/account_view.xml',
    ],

    'images': [
        'static/description/cover.png',
        'static/description/icon.png',
    ],

    'price': 120,
    'currency': 'EUR',
}
