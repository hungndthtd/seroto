# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AcademicIntake(models.Model):
    _name = 'academic.intake'
    _description = 'Đợt học'

    name = fields.Char(string='Tên đợt học', required=True)
    course_id = fields.Many2one('academic.course', string='Khóa học', required=True)
    date_start = fields.Date(string='Ngày bắt đầu')
    date_end = fields.Date(string='Ngày kết thúc')
    active = fields.Boolean(string='Kích hoạt', default=True)

    @api.depends('name', 'course_id.name')
    def _compute_display_name(self):
        for intake in self:
            if intake.course_id:
                intake.display_name = f"{intake.name} - {intake.course_id.name}"
            else:
                intake.display_name = intake.name
