{
    "name": "Realty",
    "version": "1.0",
    "depends": [
        "base",
        "mail",
        "auth_signup",
        "web",
        "contacts",
        "VietNam_administrative",
        "hr",
        "product",
        "data_recycle",
        "calendar",
    ],
    "category": "Realty",
    "summary": "Realty",
    "description": """
        - Allows admins to manage User: Job Title, User, Partner
        - Allows admins to manage Product: characteristic, status, types, home direction, group home direction, reasons for buying
        - Allows admins to manage puprchase-purpose.
    """,
    "data": [
        # views
        "views/hr_job_views.xml",
				"views/hr_job_wizard_views.xml",
        "views/realty_Real_Estate_feature_views.xml",
        "views/realty_Real_Estate_type_views.xml",
        "views/realty_tag_views.xml",
        "views/realty_policy_views.xml",
        "views/realty_Real_Estate_status_views.xml",
        "views/realty_Real_Estate_reason_views.xml",
        "views/realty_Real_Estate_group_home_direction_views.xml",
        "views/realty_Real_Estate_home_direction_views.xml",
        "views/region_views.xml",
        "views/res_users_views.xml",
        "views/res_partner_views.xml",
        "views/hr_department_views.xml",
        "views/realty_assign_employee_wizard_views.xml",
        "views/res_company_views.xml",
        "views/realty_Real_Estate_land_title_views.xml",
        "views/realty_Real_Estate_unit_price_views.xml",
        "views/mail_tracking_value_views.xml",
        "views/product_template_views.xml",
        "views/realty_Report_client_feedback_views.xml",
        "views/realty_Report_owner_feedback_views.xml",
        "views/realty_Real_Estate_report_views.xml",
        "views/realty_Notify_moderator_assignment_sequence_views.xml",
        "views/realty_Notify_guideline_views.xml",
        "views/realty_Notify_urgent_buying_views.xml",
        "views/realty_Notify_congratulation_views.xml",
        "views/realty_Notify_notification_views.xml",
        "views/realty_Notify_wizard_views.xml",
        "views/realty_Notify_moderator_guideline_views.xml",
        "views/realty_Notify_reject_reason_views.xml",
        "views/realty_Notify_remove_reason_views.xml",
        "views/ir_attachment_views.xml",
        "views/realty_permission_tracker_views.xml",
        "views/realty_Comment_wizard_views.xml",
        "views/realty_Product_wizard_views.xml",
        "views/realty_User_Evaluation_wizard_views.xml",
        "views/realty_user_evaluation_views.xml",
				"views/hr_employee_views.xml",
				"views/hr_employee_wizard_views.xml",
        # templates
        "templates/signup_inherit_template.xml",
        "templates/my_profile_template.xml",
        # menu
        "menu/menu.xml",
        "menu/menu_address_root.xml",
        "menu/menu_product_root.xml",
        "menu/menu_user_root.xml",
        "menu/menu_report_root.xml",
        "menu/menu_notify_root.xml",
        "menu/menu_more_root.xml",
				"menu/hr_views_extend.xml",
        # data
        "data/res_groups.xml",
        "data/ir_rule.xml",
        "data/unit_price.xml",
        "data/ir_config_parameter.xml",
        "data/hr_job.xml",
        "data/res_users.xml",
        #"data/data_recycle.xml",  # comment this line before install module realty_bds, then uncomment it and upgrade module to have feature of auto clean orphaned attachments
        "data/permission_tracker.xml",
        # security
        "security/ir.model.access.csv",
    ],
    "assets": {
        "web.assets_frontend": [
            # signup
            # js
            "realty_bds/static/src/signup/js/signup_dynamic_address.js",
            "realty_bds/static/src/signup/js/signup_file_input.js",
            # css
            "realty_bds/static/src/signup/css/signup_file_input.css",
            # my_profile
            # js
            "realty_bds/static/src/my_profile/js/notify.js",
            # css
            "realty_bds/static/src/my_profile/css/style.css",
        ],
        "web.assets_backend": [
            # filter
            # xml
            "realty_bds/static/src/filter/xml/tooltip.xml",
            "realty_bds/static/src/filter/xml/many2many_chip.xml",
            "realty_bds/static/src/filter/xml/filter_dialog.xml",
            "realty_bds/static/src/filter/xml/web_SearchBar_patch.xml",
            "realty_bds/static/src/filter/xml/web_SearchBar_Toggler_patch.xml",
            "realty_bds/static/src/filter/xml/web_ControlPanel_patch.xml",
            # js
            "realty_bds/static/src/filter/js/utils_filter.js",
            "realty_bds/static/src/filter/js/many2many_chip.js",
            "realty_bds/static/src/filter/js/filter_dialog.js",
            "realty_bds/static/src/filter/js/ControlPanel_patch.js",
            # scss
            "realty_bds/static/src/filter/scss/many2many_chip.scss",
            "realty_bds/static/src/filter/scss/filter_dialog.scss",
            "realty_bds/static/src/filter/scss/web_ControlPanel.scss",
            # many2many_image
            # xml
            "realty_bds/static/src/many2many_image/xml/photo_lightbox.xml",
            "realty_bds/static/src/many2many_image/xml/many2many_image.xml",
            # js
            "realty_bds/static/src/many2many_image/js/constants.js",
            "realty_bds/static/src/many2many_image/js/validated_file_input.js",
            "realty_bds/static/src/many2many_image/js/photo_lightbox.js",
            "realty_bds/static/src/many2many_image/js/many2many_image.js",
            # scss
            "realty_bds/static/src/many2many_image/scss/photo_lightbox.scss",
            "realty_bds/static/src/many2many_image/scss/many2many_image.scss",
            # one2many_file
            # xml
            "realty_bds/static/src/one2many_file/xml/one2many_file.xml",
            # js
            "realty_bds/static/src/one2many_file/js/one2many_file.js",
            # realty_comment
            # xml
            "realty_bds/static/src/realty_comment/xml/comment_dialog.xml",
            "realty_bds/static/src/realty_comment/xml/comment_item.xml",
            # js
            "realty_bds/static/src/realty_comment/js/realty_comment_action.js",
            "realty_bds/static/src/realty_comment/js/realty_comment_dialog.js",
            "realty_bds/static/src/realty_comment/js/realty_comment_item.js",
            # scss
            "realty_bds/static/src/realty_comment/scss/realty_comment_dialog.scss",
            # realty_notify
            # css
            "realty_bds/static/src/realty_notify/css/notify_kanban.css",
            # moderator_guideline
            # xml
            "realty_bds/static/src/moderator_guideline/xml/moderator_guideline_info.xml",
            "realty_bds/static/src/moderator_guideline/xml/guideline_dialog.xml",
            # js
            "realty_bds/static/src/moderator_guideline/js/guideline_dialog.js",
            "realty_bds/static/src/moderator_guideline/js/guideline_controller.js",
            # scss
            "realty_bds/static/src/moderator_guideline/scss/guideline_dialog.scss",
            # boolean_subscriber
            # xml
            "realty_bds/static/src/boolean_subscriber/xml/subscribe_button.xml",
            # js
            "realty_bds/static/src/boolean_subscriber/js/boolean_subscriber.js",
            # scss
            "realty_bds/static/src/boolean_subscriber/scss/subsribe_button.scss",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
} # type: ignore
