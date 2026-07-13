# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AcademicSession(models.Model):
    _name = 'academic.session'
    _description = 'Buổi học'
    _order = 'date_start'

    name = fields.Char(string='Tên buổi học', required=True)
    class_id = fields.Many2one('academic.class', string='Lớp học', required=True, ondelete='cascade')
    date_start = fields.Datetime(string='Thời gian bắt đầu', required=True)
    date_end = fields.Datetime(string='Thời gian kết thúc')
    
    attendance_ids = fields.One2many('academic.attendance', 'session_id', string='Điểm danh')

    def action_load_students(self):
        self.ensure_one()
        enrollments = self.env['academic.enrollment'].search([
            ('class_id', '=', self.class_id.id),
            ('state', '=', 'enrolled')
        ])
        for enrollment in enrollments:
            existing = self.env['academic.attendance'].search([
                ('session_id', '=', self.id),
                ('student_id', '=', enrollment.student_id.id)
            ], limit=1)
            if not existing:
                self.env['academic.attendance'].create({
                    'session_id': self.id,
                    'student_id': enrollment.student_id.id,
                    'state': 'present',
                })

