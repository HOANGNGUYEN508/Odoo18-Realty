{
    'name': 'Realty',
    'version': '1.0',
    'depends': [
				'base',
				'mail',
				'auth_signup',
				'web',
				'contacts', 
				'VietNam_administrative', 
				'hr',
				'product',
				'data_recycle',
				'calendar',
		],
    'category': 'Realty',
    'summary': 'Realty',
    "description": """
        - Allows admins to manage User: Job Title, User, Partner
        - Allows admins to manage Product: characteristic, status, types, home direction, group home direction, reasons for buying
        - Allows admins to manage puprchase-purpose.
    """,
    'data': [
        'data/res_groups.xml',
        'data/ir_rule.xml',
        'security/ir.model.access.csv',
        'views/menu.xml',
        'views/hr_job_views.xml',
        'views/hr_job_menu.xml',
        'views/realty_Real_Estate_feature_views.xml',
        'views/realty_Real_Estate_feature_menu.xml',
        'views/realty_Real_Estate_type_views.xml',
        'views/realty_Real_Estate_type_menu.xml',
        'views/realty_tag_views.xml',
        'views/realty_tag_menu.xml',
        'views/realty_policy_views.xml',
        'views/realty_policy_menu.xml',
        'views/realty_Real_Estate_status_views.xml',
        'views/realty_Real_Estate_status_menu.xml',
        'views/realty_Real_Estate_reason_views.xml',
        'views/realty_Real_Estate_reason_menu.xml',
        'views/realty_Real_Estate_group_home_direction_views.xml',
        'views/realty_Real_Estate_group_home_direction_menu.xml',
        'views/realty_Real_Estate_home_direction_views.xml',
        'views/realty_Real_Estate_home_direction_menu.xml',
        'views/region_views.xml',
        'views/region_menu.xml',
        'views/res_users_views.xml',
        'views/res_partner_views.xml',
        'views/res_users_menu.xml',
        'views/signup_inherit_template.xml',
        'views/hr_department_views.xml',
        'views/hr_department_menu.xml',
        'views/realty_assign_employee_wizard_views.xml',
        'views/res_company_views.xml',
        'views/res_company_menu.xml',
				'views/realty_Real_Estate_land_tittle_views.xml',
				'views/realty_Real_Estate_land_tittle_menu.xml',
				'views/realty_Real_Estate_unit_price_views.xml',
				'views/realty_Real_Estate_unit_price_menu.xml',
        'data/unit_price.xml',
        'views/product_template_views.xml',
        'views/product_template_menu.xml',
				'data/ir_config_parameter.xml',
				'data/data_recycle.xml',
				'views/my_profile_template.xml',
				'data/hr_job.xml',
				'data/res_users.xml',
				'views/realty_Report_client_feedback_views.xml',
				'views/realty_Report_client_feedback_menu.xml',
				'views/realty_Report_owner_feedback_views.xml',
				'views/realty_Report_owner_feedback_menu.xml',
				'views/realty_Real_Estate_report_views.xml',
				'views/realty_Real_Estate_report_menu.xml',
    ],
    'assets': {
        'web.assets_frontend': [
						# signup
						# js
						'realty_bds/static/src/signup/signup_dynamic_address.js',

						#my_profile
            #js
            'realty_bds/static/src/my_profile/js/notify.js',
						#css
            'realty_bds/static/src/my_profile/css/style.css',
        ],
				'web.assets_backend': [	
						# filter
						# xml
						'realty_bds/static/src/filter/xml/tooltip.xml',
            'realty_bds/static/src/filter/xml/many2many_chip.xml',			
            'realty_bds/static/src/filter/xml/filter_dialog.xml',
            'realty_bds/static/src/filter/xml/web_SearchBar_patch.xml',
            'realty_bds/static/src/filter/xml/web_SearchBar_Toggler_patch.xml',
            'realty_bds/static/src/filter/xml/web_ControlPanel_patch.xml',
						# js
						'realty_bds/static/src/filter/js/utils_filter.js',
            'realty_bds/static/src/filter/js/many2many_chip.js',             
            'realty_bds/static/src/filter/js/filter_dialog.js',    
            'realty_bds/static/src/filter/js/ControlPanel_patch.js',
						# scss      
						'realty_bds/static/src/filter/scss/many2many_chip.scss',
            'realty_bds/static/src/filter/scss/filter_dialog.scss',
            'realty_bds/static/src/filter/scss/web_ControlPanel.scss',

						# many2many_image
						# xml
						'realty_bds/static/src/many2many_image/xml/photo_lightbox.xml',
						'realty_bds/static/src/many2many_image/xml/many2many_image.xml',
						# js
						'realty_bds/static/src/many2many_image/js/validated_file_input.js',
						'realty_bds/static/src/many2many_image/js/photo_lightbox.js',
						'realty_bds/static/src/many2many_image/js/many2many_image.js',    
						# scss
            'realty_bds/static/src/many2many_image/scss/many2many_image.scss',
				]
    },
    "installable": True,
    "application": True,
    'auto_install': False,
    'license': 'LGPL-3',
}