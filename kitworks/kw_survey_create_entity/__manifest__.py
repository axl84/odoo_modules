{
    'name': 'Survey create entity',

    'summary': 'Creating any model entity after survey finishing and fill up '
               'model fields',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'category': 'Other Category',
    'license': 'OPL-1',
    'version': '17.0.1.0.13',

    'depends': [
        'survey', 'kw_survey_attachment',
    ],
    'data': [
        'security/ir.model.access.csv',

        'views/survey_view.xml',
    ],
    'installable': True,

}
