# -*- coding: utf-8 -*-

from odoo import models, fields

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    course_id = fields.Many2one('academic.course', string='Khóa học quan tâm')
    google_form_response_id = fields.Char(
        string='Mã phản hồi Google Form', index=True, copy=False,
        help='ID phản hồi (Form Response ID) từ Google Form - dùng để tránh tạo trùng '
             'lead nếu Apps Script gửi lại cùng 1 dòng (vd do lỗi mạng, chạy lại script).',
    )
