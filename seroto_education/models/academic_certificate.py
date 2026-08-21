# -*- coding: utf-8 -*-

import random
from odoo import models, fields, api

class AcademicCertificate(models.Model):
    _name = 'academic.certificate'
    _description = 'Chứng chỉ'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    code = fields.Char(string='Mã chứng chỉ', readonly=True, copy=False)
    name = fields.Char(string='Tên chứng chỉ', compute='_compute_name', store=True, readonly=False)
    student_id = fields.Many2one('res.partner', string='Học viên', required=True)
    course_id = fields.Many2one('academic.course', string='Khóa học', required=True)
    class_id = fields.Many2one('academic.class', string='Lớp học', required=True)
    # Liên kết ngược tới đúng lượt Ghi danh đã sinh ra chứng chỉ này (xem
    # academic_enrollment.py, action_complete()) - trước đây chỉ suy luận gián tiếp qua
    # trùng student_id/course_id/class_id, không phân biệt được nếu 1 học viên có 2 lượt
    # Ghi danh khác nhau vào cùng 1 lớp (VD học lại).
    enrollment_id = fields.Many2one(
        'academic.enrollment', string='Ghi danh', readonly=True, copy=False,
    )
    date_issue = fields.Date(string='Ngày cấp', default=fields.Date.context_today)

    @api.depends('student_id', 'course_id')
    def _compute_name(self):
        for rec in self:
            if rec.student_id and rec.course_id:
                rec.name = f"Chứng chỉ {rec.course_id.name} - {rec.student_id.name}"
            else:
                rec.name = "Chứng chỉ khóa học"
    
    grade = fields.Selection([
        ('passed', 'Đạt'),
        ('failed', 'Không đạt'),
        ('excellent', 'Xuất sắc')
    ], string='Xếp loại', default='passed', required=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code'):
                # Simple unique code generation: CERT - Year - 4 random digits
                year = fields.Date.context_today(self).year
                random_digits = ''.join([str(random.randint(0, 9)) for _ in range(4)])
                vals['code'] = f"CERT-{year}-{random_digits}"
        return super(AcademicCertificate, self).create(vals_list)
