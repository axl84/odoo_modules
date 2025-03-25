{
    'name': 'WayForPay Payment Provider',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'category': 'Customizations',
    'license': 'OPL-1',
    'version': '17.0.1.6.0',

    'depends': ['payment', 'kw_payment_base', 'account'],
    'data': [
        'security/ir.model.access.csv',

        'views/payment_views.xml',
        'views/payment_wayforpay_templates.xml',
        'views/transaction_views.xml',

        'data/payment_provider_data.xml',
    ],
    'installable': True,

    'images': [
        'static/description/cover.png',
        'static/description/icon.png',
    ],
    'uninstall_hook': 'uninstall_hook',
    'price': 100,
    'currency': 'EUR',
}
