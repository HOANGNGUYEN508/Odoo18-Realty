{
    "name": "VietNam_administrative",
    'version': '1.0',
    "depends": ['base','mail'],
    "category": "Realty",
    "summary": "Creates Province",
    "description": """
        - Allows admins to manage genders.
    """,
    "data": [
        'data/res_groups.xml',
        'security/ir.model.access.csv',
        'views/country_views.xml',
        'views/province_views.xml',
        'views/district_views.xml',
        'views/commune_views.xml',
        'views/menu.xml',
    ],
    "installable": True,
    "application": False,
    'auto_install': False,
    'license': 'LGPL-3',
}
