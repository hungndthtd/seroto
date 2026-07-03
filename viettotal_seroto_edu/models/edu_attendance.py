# -*- coding: utf-8 -*-
"""
edu_attendance.py
Quản lý điểm danh từng buổi học: có mặt, vắng, trễ, phép.
Tự động cập nhật tiến độ học tập (edu.learning.progress).
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class EduAttendance(models.Model):
    _name = 'edu.attendance'
    _description = 'Điểm danh buổi học'
    _order = 'session_id, student_id'

    session_id = fields.Many2one(
        comodel_name='edu.session',
        string='Buổi học',
        required=True,
        ondelete='cascade',
    )
    class_id = fields.Many2one(
        comodel_name='edu.course.class',
        string='Lớp học',
        related='session_id.class_id',
        store=True,
    )
    date_session = fields.Date(
        string='Ngày học',
        related='session_id.date_session',
        store=True,
    )
    student_id = fields.Many2one(
        comodel_name='edu.student',
        string='Học viên',
        required=True,
        ondelete='cascade',
    )
    status = fields.Selection(
        selection=[
            ('present',     'Có mặt'),
            ('absent',      'Vắng không phép'),
            ('absent_leave','Vắng có phép'),
            ('late',        'Đi trễ'),
            ('early_leave', 'Về sớm'),
            ('online',      'Học online'),
        ],
        string='Trạng thái điểm danh',
        required=True,
        default='present',
    )
    check_in_time = fields.Float(string='Giờ vào (thực tế)', help='VD: 18.25 = 18:15')
    check_out_time = fields.Float(string='Giờ ra (thực tế)')
    minutes_late = fields.Integer(string='Số phút đi trễ', default=0)

    # ── Ghi chú & Phép ────────────────────────────────────────────────────────
    leave_reason = fields.Text(string='Lý do nghỉ phép')
    note = fields.Text(string='Ghi chú thêm')
    notified_parent = fields.Boolean(string='Đã thông báo phụ huynh', default=False)
    notified_at = fields.Datetime(string='Thời gian thông báo PH')

    # ── Người điểm danh ────────────────────────────────────────────────────────
    recorded_by = fields.Many2one(
        comodel_name='res.users',
        string='Người điểm danh',
        default=lambda self: self.env.user,
    )
    record_date = fields.Datetime(string='Thời điểm ghi nhận', default=fields.Datetime.now)

    # ── Tính chuyên cần ────────────────────────────────────────────────────────
    is_counted_present = fields.Boolean(
        string='Tính là có mặt',
        compute='_compute_is_counted_present',
        store=True,
        help='Có mặt, đi trễ nhẹ, học online đều tính là có mặt.',
    )

    @api.depends('status')
    def _compute_is_counted_present(self):
        present_statuses = {'present', 'late', 'online', 'early_leave'}
        for rec in self:
            rec.is_counted_present = rec.status in present_statuses

    # ── After write: cập nhật tiến độ ────────────────────────────────────────
    def _update_learning_progress(self):
        """Cập nhật bản ghi tiến độ sau khi điểm danh thay đổi."""
        for rec in self:
            progress = self.env['edu.learning.progress'].search([
                ('student_id', '=', rec.student_id.id),
                ('class_id', '=', rec.class_id.id),
            ], limit=1)
            if progress:
                attended = self.search_count([
                    ('student_id', '=', rec.student_id.id),
                    ('class_id', '=', rec.class_id.id),
                    ('is_counted_present', '=', True),
                ])
                progress.sessions_attended = attended

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._update_learning_progress()
        return records

    def write(self, vals):
        result = super().write(vals)
        if 'status' in vals:
            self._update_learning_progress()
        return result

    _sql_constraints = [
        ('session_student_unique', 'unique(session_id, student_id)',
         'Mỗi học viên chỉ có một bản ghi điểm danh cho mỗi buổi học!'),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Wizard tạo điểm danh hàng loạt cho một buổi học
# ─────────────────────────────────────────────────────────────────────────────
class EduAttendanceWizard(models.TransientModel):
    _name = 'edu.attendance.wizard'
    _description = 'Tạo điểm danh cho buổi học'

    session_id = fields.Many2one('edu.session', string='Buổi học', required=True)
    class_id = fields.Many2one(
        'edu.course.class',
        related='session_id.class_id',
        string='Lớp học',
    )
    line_ids = fields.One2many('edu.attendance.wizard.line', 'wizard_id', string='Danh sách học viên')

    @api.onchange('session_id')
    def _onchange_session_id(self):
        if self.session_id:
            enrolled = self.session_id.class_id.enrollment_ids.filtered(
                lambda e: e.state in ('studying', 'registered')
            )
            self.line_ids = [(5, 0, 0)] + [
                (0, 0, {
                    'student_id': e.student_id.id,
                    'status': 'present',
                })
                for e in enrolled
            ]

    def action_confirm(self):
        self.ensure_one()
        for line in self.line_ids:
            existing = self.env['edu.attendance'].search([
                ('session_id', '=', self.session_id.id),
                ('student_id', '=', line.student_id.id),
            ], limit=1)
            if not existing:
                self.env['edu.attendance'].create({
                    'session_id': self.session_id.id,
                    'student_id': line.student_id.id,
                    'status': line.status,
                    'note': line.note,
                })
        self.session_id.write({'state': 'completed'})
        return {'type': 'ir.actions.act_window_close'}


class EduAttendanceWizardLine(models.TransientModel):
    _name = 'edu.attendance.wizard.line'
    _description = 'Dòng điểm danh wizard'

    wizard_id = fields.Many2one('edu.attendance.wizard', required=True, ondelete='cascade')
    student_id = fields.Many2one('edu.student', string='Học viên', required=True)
    status = fields.Selection(
        selection=[
            ('present',      'Có mặt'),
            ('absent',       'Vắng không phép'),
            ('absent_leave', 'Vắng có phép'),
            ('late',         'Đi trễ'),
            ('online',       'Học online'),
        ],
        string='Trạng thái',
        default='present',
        required=True,
    )
    note = fields.Char(string='Ghi chú')
