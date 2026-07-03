# -*- coding: utf-8 -*-
"""
edu_learning.py
Quản lý nội dung học tập: giáo trình, tài liệu, bài tập, bài kiểm tra nhanh.
Hỗ trợ theo dõi tiến độ học tập từng học viên.
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


# ─────────────────────────────────────────────────────────────────────────────
# Giáo trình / Syllabus
# ─────────────────────────────────────────────────────────────────────────────
class EduSyllabus(models.Model):
    _name = 'edu.syllabus'
    _description = 'Giáo trình khoá học'
    _order = 'course_id, sequence'

    name = fields.Char(string='Tên giáo trình / Chương', required=True)
    sequence = fields.Integer(string='Thứ tự', default=10)
    course_id = fields.Many2one('edu.course', string='Khoá học', required=True, ondelete='cascade')
    description = fields.Text(string='Mô tả nội dung')
    duration_hours = fields.Float(string='Thời lượng (giờ)')

    unit_ids = fields.One2many('edu.syllabus.unit', 'syllabus_id', string='Bài học / Đơn vị')
    unit_count = fields.Integer(compute='_compute_unit_count', string='Số bài')

    @api.depends('unit_ids')
    def _compute_unit_count(self):
        for rec in self:
            rec.unit_count = len(rec.unit_ids)


class EduSyllabusUnit(models.Model):
    _name = 'edu.syllabus.unit'
    _description = 'Bài học / Đơn vị học tập'
    _order = 'syllabus_id, sequence'

    name = fields.Char(string='Tên bài học', required=True)
    sequence = fields.Integer(string='Thứ tự', default=10)
    syllabus_id = fields.Many2one('edu.syllabus', string='Chương', required=True, ondelete='cascade')
    objective = fields.Text(string='Mục tiêu bài học')
    content = fields.Html(string='Nội dung')
    duration_minutes = fields.Integer(string='Thời lượng (phút)')

    material_ids = fields.One2many('edu.material', 'unit_id', string='Tài liệu đính kèm')


# ─────────────────────────────────────────────────────────────────────────────
# Tài liệu học tập
# ─────────────────────────────────────────────────────────────────────────────
class EduMaterial(models.Model):
    _name = 'edu.material'
    _description = 'Tài liệu học tập'
    _order = 'name asc'

    name = fields.Char(string='Tên tài liệu', required=True)
    material_type = fields.Selection(
        selection=[
            ('document',  'Tài liệu / PDF'),
            ('video',     'Video'),
            ('audio',     'Audio'),
            ('link',      'Đường dẫn'),
            ('exercise',  'Bài tập'),
            ('other',     'Khác'),
        ],
        string='Loại tài liệu',
        default='document',
        required=True,
    )
    unit_id = fields.Many2one('edu.syllabus.unit', string='Bài học', ondelete='set null')
    course_id = fields.Many2one('edu.course', string='Khoá học', ondelete='set null')
    class_id = fields.Many2one('edu.course.class', string='Lớp học', ondelete='set null')
    session_id = fields.Many2one('edu.session', string='Buổi học', ondelete='set null')

    description = fields.Text(string='Mô tả')
    url = fields.Char(string='Đường dẫn (URL / Drive)')
    attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        string='File đính kèm',
    )
    is_public = fields.Boolean(string='Học viên xem được', default=True)
    note = fields.Text(string='Ghi chú giáo viên')


# ─────────────────────────────────────────────────────────────────────────────
# Bài tập về nhà / Assignment
# ─────────────────────────────────────────────────────────────────────────────
class EduAssignment(models.Model):
    _name = 'edu.assignment'
    _description = 'Bài tập / Nhiệm vụ học tập'
    _inherit = ['mail.thread']
    _order = 'due_date asc'

    name = fields.Char(string='Tên bài tập', required=True)
    class_id = fields.Many2one('edu.course.class', string='Lớp học', required=True, ondelete='cascade')
    session_id = fields.Many2one('edu.session', string='Buổi học giao bài', ondelete='set null')
    teacher_id = fields.Many2one(
        'edu.teacher', string='Giáo viên giao',
        related='class_id.teacher_id', store=True,
    )

    description = fields.Html(string='Nội dung / Yêu cầu')
    due_date = fields.Date(string='Hạn nộp', tracking=True)
    max_score = fields.Float(string='Điểm tối đa', default=10.0)
    assignment_type = fields.Selection(
        selection=[
            ('homework',    'Bài tập về nhà'),
            ('project',     'Dự án'),
            ('in_class',    'Bài tập trên lớp'),
            ('presentation','Thuyết trình'),
        ],
        string='Loại bài tập',
        default='homework',
    )

    submission_ids = fields.One2many('edu.assignment.submission', 'assignment_id', string='Bài nộp')
    submission_count = fields.Integer(compute='_compute_submission_count', string='Số bài nộp')
    attachment_ids = fields.Many2many('ir.attachment', string='Tài liệu đính kèm')

    @api.depends('submission_ids')
    def _compute_submission_count(self):
        for rec in self:
            rec.submission_count = len(rec.submission_ids)


class EduAssignmentSubmission(models.Model):
    _name = 'edu.assignment.submission'
    _description = 'Bài nộp của học viên'
    _order = 'assignment_id, student_id'

    assignment_id = fields.Many2one('edu.assignment', string='Bài tập', required=True, ondelete='cascade')
    student_id = fields.Many2one('edu.student', string='Học viên', required=True, ondelete='cascade')

    state = fields.Selection(
        selection=[
            ('not_submitted', 'Chưa nộp'),
            ('submitted',     'Đã nộp'),
            ('late',          'Nộp trễ'),
            ('graded',        'Đã chấm'),
        ],
        string='Trạng thái',
        default='not_submitted',
    )
    date_submitted = fields.Datetime(string='Ngày nộp')
    score = fields.Float(string='Điểm chấm')
    feedback = fields.Text(string='Nhận xét của giáo viên')
    attachment_ids = fields.Many2many('ir.attachment', string='File bài nộp')
    note = fields.Text(string='Ghi chú')


# ─────────────────────────────────────────────────────────────────────────────
# Tiến độ học tập
# ─────────────────────────────────────────────────────────────────────────────
class EduLearningProgress(models.Model):
    _name = 'edu.learning.progress'
    _description = 'Tiến độ học tập học viên'
    _order = 'student_id, class_id'

    student_id = fields.Many2one('edu.student', string='Học viên', required=True, ondelete='cascade')
    class_id = fields.Many2one('edu.course.class', string='Lớp học', required=True, ondelete='cascade')
    enrollment_id = fields.Many2one('edu.enrollment', string='Đăng ký học')

    # ── Tiến độ ──────────────────────────────────────────────────────────────
    sessions_total = fields.Integer(
        string='Tổng số buổi',
        related='class_id.session_count', store=True,
    )
    sessions_attended = fields.Integer(string='Số buổi đã học', default=0)
    attendance_rate = fields.Float(
        string='Tỷ lệ chuyên cần (%)',
        compute='_compute_attendance_rate',
        store=True,
    )
    progress_percent = fields.Float(string='Hoàn thành (%)', default=0.0)

    # ── Kết quả học tập ──────────────────────────────────────────────────────
    average_score = fields.Float(string='Điểm trung bình')
    latest_score = fields.Float(string='Điểm gần nhất')
    teacher_comment = fields.Text(string='Nhận xét của giáo viên')

    # ── Cờ chú ý ─────────────────────────────────────────────────────────────
    needs_attention = fields.Boolean(
        string='Cần chú ý / Chăm sóc đặc biệt',
        default=False,
        help='Giáo viên đánh dấu để nhân viên chăm sóc follow up',
    )
    attention_note = fields.Text(string='Lý do cần chú ý')
    last_update = fields.Date(string='Cập nhật lần cuối', default=fields.Date.today)

    @api.depends('sessions_total', 'sessions_attended')
    def _compute_attendance_rate(self):
        for rec in self:
            if rec.sessions_total:
                rec.attendance_rate = (rec.sessions_attended / rec.sessions_total) * 100
            else:
                rec.attendance_rate = 0.0

    _sql_constraints = [
        ('student_class_unique', 'unique(student_id, class_id)',
         'Mỗi học viên chỉ có một bản ghi tiến độ cho mỗi lớp học!'),
    ]
