# -*- coding: utf-8 -*-
"""
edu_assessment.py
Quản lý kiểm tra, đánh giá và kết quả học tập:
- Loại bài kiểm tra (đầu vào, giữa kỳ, cuối kỳ, mock test…)
- Bài kiểm tra (Exam) gắn với lớp học
- Điểm từng học viên (Result)
- Thống kê tổng hợp
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


# ─────────────────────────────────────────────────────────────────────────────
# Loại bài kiểm tra
# ─────────────────────────────────────────────────────────────────────────────
class EduAssessmentType(models.Model):
    _name = 'edu.assessment.type'
    _description = 'Loại bài kiểm tra'
    _order = 'sequence, name'

    name = fields.Char(string='Tên loại kiểm tra', required=True)
    sequence = fields.Integer(default=10)
    code = fields.Char(string='Mã')
    weight = fields.Float(string='Hệ số (%)', default=100.0, help='Tỷ trọng trong điểm tổng kết')
    description = fields.Text(string='Mô tả')
    active = fields.Boolean(default=True)


# ─────────────────────────────────────────────────────────────────────────────
# Bài kiểm tra / Kỳ thi
# ─────────────────────────────────────────────────────────────────────────────
class EduExam(models.Model):
    _name = 'edu.exam'
    _description = 'Bài kiểm tra / Kỳ thi'
    _inherit = ['mail.thread']
    _order = 'date_exam desc'

    name = fields.Char(string='Tên bài kiểm tra', required=True, tracking=True)
    exam_code = fields.Char(string='Mã đề thi', copy=False)
    assessment_type_id = fields.Many2one(
        'edu.assessment.type', string='Loại kiểm tra', required=True,
    )
    class_id = fields.Many2one(
        'edu.course.class', string='Lớp học', required=True, ondelete='cascade', tracking=True,
    )
    course_id = fields.Many2one(
        'edu.course', related='class_id.course_id', store=True, string='Khoá học',
    )
    teacher_id = fields.Many2one(
        'edu.teacher', related='class_id.teacher_id', store=True, string='Giáo viên',
    )
    session_id = fields.Many2one(
        'edu.session', string='Buổi kiểm tra', ondelete='set null',
    )

    date_exam = fields.Date(string='Ngày kiểm tra', required=True, tracking=True)
    time_start = fields.Float(string='Giờ bắt đầu')
    duration_minutes = fields.Integer(string='Thời lượng (phút)', default=60)

    # ── Thang điểm ────────────────────────────────────────────────────────────
    max_score = fields.Float(string='Điểm tối đa', default=10.0)
    pass_score = fields.Float(string='Điểm đạt', default=5.0)
    scoring_method = fields.Selection(
        selection=[
            ('points',    'Thang điểm 10'),
            ('band',      'Band score (IELTS 0-9)'),
            ('percent',   'Phần trăm (%)'),
            ('toeic',     'TOEIC (10-990)'),
            ('pass_fail', 'Đạt / Không đạt'),
        ],
        string='Phương thức chấm',
        default='points',
    )

    # ── Nội dung ────────────────────────────────────────────────────────────
    description = fields.Text(string='Mô tả / Phạm vi đề thi')
    instructions = fields.Html(string='Hướng dẫn làm bài')
    attachment_ids = fields.Many2many('ir.attachment', string='Đề thi / Tài liệu')

    # ── Kết quả ────────────────────────────────────────────────────────────
    result_ids = fields.One2many('edu.exam.result', 'exam_id', string='Kết quả học viên')
    result_count = fields.Integer(compute='_compute_result_stats', string='Số bài')
    pass_count = fields.Integer(compute='_compute_result_stats', string='Đạt')
    fail_count = fields.Integer(compute='_compute_result_stats', string='Không đạt')
    average_score = fields.Float(compute='_compute_result_stats', string='Điểm TB', store=True)
    pass_rate = fields.Float(compute='_compute_result_stats', string='Tỷ lệ đạt (%)', store=True)

    state = fields.Selection(
        selection=[
            ('draft',     'Chưa thi'),
            ('done',      'Đã thi – chờ chấm'),
            ('graded',    'Đã có kết quả'),
            ('cancelled', 'Huỷ'),
        ],
        string='Trạng thái',
        default='draft',
        tracking=True,
    )

    @api.depends('result_ids', 'result_ids.score', 'result_ids.is_passed')
    def _compute_result_stats(self):
        for rec in self:
            results = rec.result_ids.filtered(lambda r: r.state == 'graded')
            rec.result_count = len(results)
            rec.pass_count = len(results.filtered('is_passed'))
            rec.fail_count = rec.result_count - rec.pass_count
            if rec.result_count:
                rec.average_score = sum(results.mapped('score')) / rec.result_count
                rec.pass_rate = (rec.pass_count / rec.result_count) * 100
            else:
                rec.average_score = 0.0
                rec.pass_rate = 0.0

    def action_generate_results(self):
        """Tạo bản ghi kết quả cho tất cả học viên trong lớp."""
        self.ensure_one()
        enrolled = self.class_id.enrollment_ids.filtered(
            lambda e: e.state in ('studying', 'registered')
        )
        for enroll in enrolled:
            existing = self.env['edu.exam.result'].search([
                ('exam_id', '=', self.id),
                ('student_id', '=', enroll.student_id.id),
            ], limit=1)
            if not existing:
                self.env['edu.exam.result'].create({
                    'exam_id': self.id,
                    'student_id': enroll.student_id.id,
                })
        self.write({'state': 'done'})

    def action_mark_graded(self):
        self.write({'state': 'graded'})


# ─────────────────────────────────────────────────────────────────────────────
# Kết quả từng học viên
# ─────────────────────────────────────────────────────────────────────────────
class EduExamResult(models.Model):
    _name = 'edu.exam.result'
    _description = 'Kết quả kiểm tra học viên'
    _order = 'exam_id, score desc'

    exam_id = fields.Many2one('edu.exam', string='Bài kiểm tra', required=True, ondelete='cascade')
    student_id = fields.Many2one('edu.student', string='Học viên', required=True, ondelete='cascade')
    class_id = fields.Many2one(
        'edu.course.class', related='exam_id.class_id', store=True, string='Lớp',
    )

    # ── Điểm thành phần (dùng cho IELTS / TOEIC) ─────────────────────────────
    score = fields.Float(string='Điểm tổng / Overall')
    score_listening = fields.Float(string='Listening')
    score_reading = fields.Float(string='Reading')
    score_writing = fields.Float(string='Writing')
    score_speaking = fields.Float(string='Speaking')

    # ── Đánh giá ────────────────────────────────────────────────────────────
    is_passed = fields.Boolean(
        string='Đạt',
        compute='_compute_is_passed',
        store=True,
    )
    grade = fields.Char(
        string='Xếp loại',
        compute='_compute_grade',
        store=True,
    )
    state = fields.Selection(
        selection=[
            ('pending', 'Chưa có điểm'),
            ('graded',  'Đã chấm'),
            ('absent',  'Vắng thi'),
        ],
        string='Trạng thái',
        default='pending',
    )

    teacher_feedback = fields.Text(string='Nhận xét của giáo viên')
    note = fields.Text(string='Ghi chú')
    date_graded = fields.Date(string='Ngày chấm')

    @api.depends('score', 'exam_id.pass_score', 'state')
    def _compute_is_passed(self):
        for rec in self:
            if rec.state == 'absent':
                rec.is_passed = False
            elif rec.exam_id and rec.exam_id.pass_score is not False:
                rec.is_passed = rec.score >= rec.exam_id.pass_score
            else:
                rec.is_passed = False

    @api.depends('score', 'exam_id.max_score', 'exam_id.scoring_method')
    def _compute_grade(self):
        for rec in self:
            method = rec.exam_id.scoring_method if rec.exam_id else 'points'
            s = rec.score
            if method == 'band':          # IELTS 0-9
                if s >= 7.5:   rec.grade = 'Xuất sắc'
                elif s >= 6.5: rec.grade = 'Giỏi'
                elif s >= 5.5: rec.grade = 'Khá'
                elif s >= 4.5: rec.grade = 'Trung bình'
                else:          rec.grade = 'Chưa đạt'
            elif method == 'toeic':       # TOEIC 10-990
                if s >= 860:   rec.grade = 'C (Advanced)'
                elif s >= 730: rec.grade = 'B2 (Upper-Intermediate)'
                elif s >= 550: rec.grade = 'B1 (Intermediate)'
                elif s >= 400: rec.grade = 'A2 (Elementary)'
                else:          rec.grade = 'A1 (Beginner)'
            elif method == 'pass_fail':
                rec.grade = 'Đạt' if rec.is_passed else 'Không đạt'
            else:                         # points / percent
                max_s = rec.exam_id.max_score or 10
                pct = (s / max_s * 100) if max_s else 0
                if pct >= 90:   rec.grade = 'Xuất sắc'
                elif pct >= 80: rec.grade = 'Giỏi'
                elif pct >= 65: rec.grade = 'Khá'
                elif pct >= 50: rec.grade = 'Trung bình'
                else:           rec.grade = 'Yếu'

    _sql_constraints = [
        ('exam_student_unique', 'unique(exam_id, student_id)',
         'Mỗi học viên chỉ có một kết quả cho mỗi bài kiểm tra!'),
    ]

    @api.constrains('score', 'exam_id')
    def _check_score(self):
        for rec in self:
            if rec.exam_id and rec.score > rec.exam_id.max_score:
                raise ValidationError(_(
                    'Điểm của %(student)s (%(score)s) vượt quá điểm tối đa %(max)s.',
                    student=rec.student_id.name,
                    score=rec.score,
                    max=rec.exam_id.max_score,
                ))
