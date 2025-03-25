{
    'name': 'ChatBot login in system',
    'version': '17.0.2.0.2',
    'license': 'OPL-1',
    'category': 'Extra Tools',
    'summary': 'Create lots of chatbots, customize chat flow, '
               'connect to multiple messengers, '
               'integrate with odoo objects ',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'depends': ['kw_chatbot_builder'],
    'data': [

        'views/step_views.xml',
    ],
    'installable': True,

    'images': [
        'static/description/cover.png',
        'static/description/icon.png',
    ],
}
