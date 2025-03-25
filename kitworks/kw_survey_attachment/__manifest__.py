{
    'name': 'File Question',

    'summary': 'Adds new File Question type, uploaded file stored in answers, '
               'survey attachment',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'category': 'Other Category',
    'license': 'OPL-1',
    'version': '17.0.1.0.5',

    'depends': [
        'survey', 'mail',
    ],
    'assets': {
        'web.assets_backend': [
            'kw_survey_attachment/static/src/css/survey_result.css',
        ],
        'survey.survey_assets': [
            'kw_survey_attachment/static/src/css/survey_front_result.css',
            'kw_survey_attachment/static/src/js/survey_form.js',
        ],
    },
    'data': [
        'views/survey_template_view.xml',
        'views/survey_user_input_line_view.xml',
        'views/survey_view.xml',
    ],
    'installable': True,

    'images': [
        'static/description/cover.png',
        'static/description/icon.png',
    ],

}
