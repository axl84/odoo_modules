{
    'name': 'Payment base',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'category': 'Customizations',
    'license': 'OPL-1',
    'version': '17.0.1.0.5',

    'depends': ['payment'],
    'data': [
        'views/transaction_views.xml',

        'wizard/payment_link_wizard_views.xml',
    ],
    'installable': True,

    'images': [
        'static/description/cover.png',
        'static/description/icon.png',
    ],
}
