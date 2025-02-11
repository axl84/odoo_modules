{
    "name": "oleg_weba_footbik_system",
    "summary": """
        """,
    "author": "Oleg (Weba)",
    "website": "https://weba.com.ua/",
    "category": "Uncategorized",
    "version": "17.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["contacts", "hr", "crm", "oleg_weba_footbik", "utm"],
    "data": [
        # "security/ir.model.access.csv",

        "views/res_partner_views.xml",
        "views/crm_lead_views.xml",
        "views/utm_source_views.xml",

        "data/utm_medium_data.xml",
        "data/utm_source_data.xml",
    ],
    "installable": True,
}
