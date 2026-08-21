# -*- coding: utf-8 -*-

from odoo import models, fields


class AcademicCourseAudience(models.Model):
    _name = 'academic.course.audience'
    _description = 'Khu vực hiển thị (Website)'
    _order = 'sequence, name'

    name = fields.Char(string='Tên khu vực', required=True)
    code = fields.Char(
        string='Mã khu vực',
        help='Mã kỹ thuật, không dấu, viết liền (vd: teacher, school). Snippet '
             '"Khóa học - Khu vực hiển thị" trên website lọc khóa học theo mã này (nhập '
             'ở panel Tùy chỉnh > Mã khu vực hiển thị) - đổi Tên khu vực thoải mái '
             'không ảnh hưởng, nhưng đổi Mã ở đây thì các snippet đã kéo trước đó (còn '
             'ghi mã cũ trên ô nhập) sẽ KHÔNG tự cập nhật theo, phải sửa lại từng snippet.',
    )
    sequence = fields.Integer(default=10)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Mã khu vực phải là duy nhất!'),
    ]
