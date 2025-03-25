{
    'name': 'Survey to lead',

    'summary': 'Create CRM lead from survey',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'category': 'Other Category',
    'license': 'OPL-1',
    'version': '17.0.1.0.5',

    'depends': [
        'crm',
        'kw_survey_create_entity',
    ],
    'data': [
        'security/ir.model.access.csv',

        'views/survey_survey_view.xml',
        'views/crm_lead_views.xml',
    ],
    'installable': True,

}
