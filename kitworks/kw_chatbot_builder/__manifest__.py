{
    'name': 'Chatbot builder',
    'version': '17.0.2.0.22',
    'license': 'OPL-1',
    'category': 'Extra Tools',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'depends': [
        'kw_chatbot', 'mail'
    ],
    'data': [
        'security/ir.model.access.csv',
        # 'data/default_bots.xml',
        'data/ir_cron_date.xml',
        'data/ir_cron_schedule.xml',
        'views/dialog_views.xml',
        'views/step_media_views.xml',
        'views/step_alias_views.xml',
        'views/step_views.xml',
        'views/conversation_views.xml',
        'views/sender_views.xml',
        'views/no_reply_views.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'kw_chatbot_builder/static/src/xml/no_reply_menu.xml',
            'kw_chatbot_builder/static/src/js/no_reply_menu.js',
        ],
    },

    # 'assets': {
    #     'web.assets_backend': [
    #         'kw_chatbot_builder/static/src/js/kw_chatbot_form_view.js',
    #         'kw_chatbot_builder/static/src/js/kw_chatbot_form_controller.js',
    #         'kw_chatbot_builder/static/src/js/'
    #         'kw_chatbot_step_form_view_dialog.js',
    #     ],
    # },
    'installable': True,
}
