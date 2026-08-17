# -*- coding: utf-8 -*-

from odoo import models, fields


class AcademicBatchWizard(models.TransientModel):
    _name = 'academic.batch.wizard'
    _description = 'Mở đợt học mới'

    course_id = fields.Many2one('academic.course', string='Khóa học', required=True)
    intake_name = fields.Char(string='Mã đợt học', required=True, placeholder='K19')
    date_start = fields.Date(string='Ngày bắt đầu dự kiến')
    date_end = fields.Date(string='Ngày kết thúc dự kiến')
    teacher_ids = fields.Many2many('res.partner', string='Giảng viên', domain=[('is_teacher', '=', True)])
    set_as_default = fields.Boolean(string='Đặt làm lớp nhận đăng ký', default=True)

    def action_confirm(self):
        self.ensure_one()
        intake = self.env['academic.intake'].create({
            'name': self.intake_name,
            'course_id': self.course_id.id,
            'date_start': self.date_start,
            'date_end': self.date_end,
        })
        new_class = self.env['academic.class'].create({
            'name': f"{self.course_id.name} - {self.intake_name}",
            'intake_id': intake.id,
            'teacher_ids': [(6, 0, self.teacher_ids.ids)],
            'state': 'draft',
        })
        if self.set_as_default:
            self.course_id.default_class_id = new_class.id
        return {'type': 'ir.actions.act_window_close'}
