# -*- coding: utf-8 -*-
{
    'name': 'Viettotal – Seroto Education',
    'version': '19.0.1.0.0',
    'summary': 'Quản lý trung tâm giáo dục: Tuyển sinh, Học viên, Lớp học, Điểm danh, Kết quả, Chứng chỉ, Chăm sóc',
    'description': """
Viettotal Seroto Education Module
===================================
Luồng chính:
    WEBSITE (Form đăng ký) → CRM Lead → Tư vấn → Sales Order → Payment
    → Hồ sơ tuyển sinh → Học viên → Lớp học → Điểm danh
    → Kiểm tra / Đánh giá → Chứng chỉ → CRM Care → Upsell
    """,
    'author': 'Viettotal',
    'website': 'https://viettotal.com',
    'category': 'Education',
    'license': 'LGPL-3',

    'depends': [
        'base',
        'mail',
        'crm',
        'sale_management',
        'utm',
        'hr',
        'website',          # <-- website route + layout
        'website_crm',      # <-- tích hợp CRM form
    ],

    'data': [
        # Security
        'security/ir.model.access.csv',

        # Sequences & base data
        'data/ir_sequence_data.xml',

        # Backend Views
        'views/view_crm_lead.xml',
        'views/view_academic.xml',
        'views/view_teacher.xml',
        'views/view_student.xml',
        'views/view_admission.xml',
        'views/view_attendance.xml',
        'views/view_learning.xml',
        'views/view_assessment.xml',
        'views/view_certificate.xml',
        'views/view_care.xml',
        'views/view_menu.xml',

        # Website Views (QWeb templates + assets)
        'views/website/assets.xml',
        'views/website/website_landing.xml',
        'views/website/website_form.xml',
        'views/website/website_thankyou_lookup.xml',
    ],

    'assets': {
        'web.assets_frontend': [
            'viettotal_seroto_edu/static/src/css/website_registration.css',
            'viettotal_seroto_edu/static/src/js/website_registration.js',
        ],
    },

    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
