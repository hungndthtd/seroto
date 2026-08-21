# -*- coding: utf-8 -*-
{
    'name': 'Seroto Education Management',
    'version': '19.0.1.8.0',
    'category': 'Education',
    'summary': 'Manage courses, classes, enrollments, attendance, and certificates without events module',
    'description': """
        This module provides complete academic management for Seroto:
        - Courses, Intakes, and Classes
        - Attendance tracking
        - Automatic student enrollment upon Sales Order payment
        - Website snippet for course registration (creating CRM Leads)
        - Student certificates
    """,
    'author': 'Seroto',
    'website': 'https://seroto.edu.vn',
    'depends': [
        'base',
        'crm',
        'sale_management',
        'website',
        'account',
    ],
    'data': [
        'security/seroto_security.xml',
        'security/ir.model.access.csv',
        'security/seroto_rules.xml',
        'data/ir_sequence_data.xml',
        'data/product_data.xml',
        'views/academic_course_views.xml',
        'views/account_move_views.xml',
        'views/academic_class_views.xml',
        'wizard/academic_batch_wizard_views.xml',
        'views/academic_enrollment_views.xml',
        'views/academic_report_metric_views.xml',
        'views/academic_attendance_views.xml',
        'views/academic_certificate_views.xml',
        'views/sale_order_views.xml',
        'views/res_partner_views.xml',
        'views/academic_menus.xml',
        'views/website_course_templates.xml',
        'views/website_foundation_templates.xml',
        'data/automated_actions.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'seroto_education/static/src/js/course_register.js',
            'seroto_education/static/src/css/course_cards.css',
        ],
        'website.website_builder_assets': [
            'seroto_education/static/src/builder/seroto_shape_option.js',
            'seroto_education/static/src/builder/seroto_shape_option.xml',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
