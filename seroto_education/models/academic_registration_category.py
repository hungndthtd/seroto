# -*- coding: utf-8 -*-

from odoo import models, fields


class AcademicRegistrationCategory(models.Model):
    _name = 'academic.registration.category'
    _description = 'Diện đăng ký (danh mục dùng chung)'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    # PHẢI khớp y hệt value của seroto.course.registration.registration_category (module
    # vtt_seroto_website, không phụ thuộc ngược - xem comment tại academic_course_question.py)
    # - dùng để so khớp diện bằng CHUỖI, không dùng id (id phụ thuộc thứ tự tạo data, dễ
    # lệch giữa các DB khác nhau).
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)

    _code_uniq = models.Constraint('unique(code)', 'Mã diện đăng ký không được trùng.')
