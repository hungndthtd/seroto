# -*- coding: utf-8 -*-

from odoo import models, fields


class AcademicCourseAudience(models.Model):
    _name = 'academic.course.audience'
    _description = 'Đối tượng khóa học'
    _order = 'sequence, name'

    name = fields.Char(string='Tên đề mục', required=True)
    code = fields.Char(
        string='Mã đề mục',
        help='Mã kỹ thuật, không dấu, viết liền (vd: teacher, school). Snippet '
             '"Khóa học - Nhóm đối tượng" trên website lọc khóa học theo mã này (nhập '
             'ở panel Tùy chỉnh > Mã đối tượng) - đổi Tên đề mục thoải mái không ảnh '
             'hưởng, nhưng đổi Mã ở đây thì các snippet đã kéo trước đó (còn ghi mã cũ '
             'trên ô nhập) sẽ KHÔNG tự cập nhật theo, phải sửa lại từng snippet.',
    )
    sequence = fields.Integer(default=10)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Mã đề mục phải là duy nhất!'),
    ]
