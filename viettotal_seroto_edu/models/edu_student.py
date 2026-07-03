# -*- coding: utf-8 -*-
"""
edu_student.py
Hồ sơ học viên – thực thể trung tâm của toàn bộ hệ thống.
Liên kết: Tuyển sinh → Học viên → Lớp học → Điểm danh → Kết quả → Chứng chỉ → Chăm sóc
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class EduStudent(models.Model):
    _name = 'edu.student'
    _description = 'Học viên'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'

    # ── Định danh ────────────────────────────────────────────────────────────
    name = fields.Char(
        string='Họ và tên',
        required=True,
        tracking=True,
    )
    student_code = fields.Char(
        string='Mã học viên',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ('active',      'Đang học'),
            ('on_leave',    'Bảo lưu'),
            ('graduated',   'Đã tốt nghiệp'),
            ('dropped_out', 'Nghỉ học'),
            ('suspended',   'Đình chỉ'),
        ],
        string='Trạng thái học',
        default='active',
        required=True,
        tracking=True,
    )

    # ── Thông tin cá nhân ────────────────────────────────────────────────────
    date_of_birth = fields.Date(string='Ngày sinh', tracking=True)
    age = fields.Integer(string='Tuổi', compute='_compute_age', store=False)
    gender = fields.Selection(
        selection=[('male', 'Nam'), ('female', 'Nữ'), ('other', 'Khác')],
        string='Giới tính',
        tracking=True,
    )
    nationality_id = fields.Many2one(
        comodel_name='res.country',
        string='Quốc tịch',
        default=lambda self: self.env.ref('base.vn', raise_if_not_found=False),
    )
    id_number = fields.Char(string='CMND / CCCD', tracking=True)
    id_issue_date = fields.Date(string='Ngày cấp')
    id_issue_place = fields.Char(string='Nơi cấp')

    phone = fields.Char(string='Số điện thoại', tracking=True)
    phone_other = fields.Char(string='Số điện thoại phụ')
    email = fields.Char(string='Email', tracking=True)
    zalo = fields.Char(string='Zalo')
    facebook = fields.Char(string='Facebook')

    address = fields.Text(string='Địa chỉ thường trú')
    current_address = fields.Text(string='Địa chỉ hiện tại')
    district = fields.Char(string='Quận/Huyện')
    province_id = fields.Many2one(comodel_name='res.country.state', string='Tỉnh/Thành phố')

    image = fields.Image(string='Ảnh học viên', max_width=256, max_height=256)

    # ── Học vấn ──────────────────────────────────────────────────────────────
    education_level = fields.Selection(
        selection=[
            ('primary',      'Tiểu học'),
            ('secondary',    'THCS'),
            ('high_school',  'THPT'),
            ('college',      'Cao đẳng'),
            ('university',   'Đại học'),
            ('postgraduate', 'Sau đại học'),
            ('other',        'Khác'),
        ],
        string='Trình độ học vấn',
    )
    major = fields.Char(string='Chuyên ngành')
    school_name = fields.Char(string='Trường đang/đã học')
    graduation_year = fields.Integer(string='Năm tốt nghiệp')
    current_job = fields.Char(string='Nghề nghiệp hiện tại')
    workplace = fields.Char(string='Nơi làm việc')

    # ── Mục tiêu học tập ─────────────────────────────────────────────────────
    learning_goal = fields.Text(string='Mục tiêu học tập')
    english_level = fields.Selection(
        selection=[
            ('beginner',      'Mất gốc / Mới bắt đầu'),
            ('elementary',    'Sơ cấp'),
            ('pre_intermediate', 'Trung cấp thấp'),
            ('intermediate',  'Trung cấp'),
            ('upper_intermediate', 'Trung cấp cao'),
            ('advanced',      'Nâng cao'),
        ],
        string='Trình độ tiếng Anh đầu vào',
    )
    target_cert = fields.Char(string='Chứng chỉ mục tiêu (IELTS, TOEIC…)')
    target_score = fields.Float(string='Điểm mục tiêu')

    # ── Liên kết hệ thống ────────────────────────────────────────────────────
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Contact (res.partner)',
        help='Liên kết với đối tác Odoo để dùng CRM, hóa đơn…',
    )
    admission_id = fields.Many2one(
        comodel_name='edu.admission',
        string='Hồ sơ tuyển sinh gốc',
        readonly=True,
    )
    parent_ids = fields.One2many(
        comodel_name='edu.parent',
        inverse_name='student_id',
        string='Phụ huynh / Người bảo lãnh',
    )

    # ── Lớp học & khoá học ───────────────────────────────────────────────────
    enrollment_ids = fields.One2many(
        comodel_name='edu.enrollment',
        inverse_name='student_id',
        string='Danh sách đăng ký học',
    )
    enrollment_count = fields.Integer(
        string='Số khoá đăng ký',
        compute='_compute_enrollment_count',
    )
    active_class_ids = fields.Many2many(
        comodel_name='edu.course.class',
        string='Lớp đang học',
        compute='_compute_active_classes',
    )

    # ── Ngày tháng ───────────────────────────────────────────────────────────
    date_enrollment = fields.Date(string='Ngày nhập học', default=fields.Date.today, tracking=True)
    date_start_study = fields.Date(string='Ngày bắt đầu học thực tế')
    date_end_study = fields.Date(string='Ngày kết thúc / nghỉ học')
    date_leave_start = fields.Date(string='Ngày bảo lưu từ')
    date_leave_end = fields.Date(string='Ngày bảo lưu đến')
    leave_reason = fields.Text(string='Lý do bảo lưu')
    drop_reason = fields.Text(string='Lý do nghỉ học')

    # ── Chăm sóc học viên ────────────────────────────────────────────────────
    care_staff_id = fields.Many2one(
        comodel_name='res.users',
        string='Nhân viên chăm sóc phụ trách',
        tracking=True,
    )
    counselor_id = fields.Many2one(
        comodel_name='res.users',
        string='Tư vấn viên ban đầu',
        tracking=True,
    )
    note = fields.Text(string='Ghi chú nội bộ')
    tag_ids = fields.Many2many(
        comodel_name='edu.student.tag',
        string='Tags',
    )

    # ── Compute ──────────────────────────────────────────────────────────────
    @api.depends('date_of_birth')
    def _compute_age(self):
        today = fields.Date.today()
        for rec in self:
            if rec.date_of_birth:
                rec.age = relativedelta(today, rec.date_of_birth).years
            else:
                rec.age = 0

    @api.depends('enrollment_ids')
    def _compute_enrollment_count(self):
        for rec in self:
            rec.enrollment_count = len(rec.enrollment_ids)

    @api.depends('enrollment_ids', 'enrollment_ids.state')
    def _compute_active_classes(self):
        for rec in self:
            active = rec.enrollment_ids.filtered(lambda e: e.state == 'studying')
            rec.active_class_ids = active.mapped('class_id')

    # ── Sequence ─────────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('student_code', _('New')) == _('New'):
                vals['student_code'] = self.env['ir.sequence'].next_by_code('edu.student') or _('New')
        return super().create(vals_list)

    # ── Actions ──────────────────────────────────────────────────────────────
    def action_view_enrollments(self):
        return {
            'type': 'ir.actions.act_window',
            'name': f'Đăng ký học – {self.name}',
            'res_model': 'edu.enrollment',
            'view_mode': 'list,form',
            'domain': [('student_id', '=', self.id)],
        }

    def action_set_on_leave(self):
        self.write({'state': 'on_leave'})

    def action_set_active(self):
        self.write({'state': 'active'})

    def action_set_graduated(self):
        self.write({'state': 'graduated'})

    def action_set_dropped(self):
        self.write({'state': 'dropped_out'})

    # ── Constraints ──────────────────────────────────────────────────────────
    _sql_constraints = [
        ('student_code_unique', 'unique(student_code)', 'Mã học viên phải là duy nhất!'),
    ]

    @api.constrains('date_of_birth')
    def _check_date_of_birth(self):
        for rec in self:
            if rec.date_of_birth and rec.date_of_birth > fields.Date.today():
                raise ValidationError(_('Ngày sinh không thể là ngày trong tương lai.'))


class EduStudentTag(models.Model):
    _name = 'edu.student.tag'
    _description = 'Tag học viên'

    name = fields.Char(string='Tên tag', required=True)
    color = fields.Integer(string='Màu', default=0)

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Tên tag phải là duy nhất!'),
    ]


class EduEnrollment(models.Model):
    """Bảng trung gian: Học viên ↔ Lớp học (nhiều-nhiều với thêm thuộc tính)."""
    _name = 'edu.enrollment'
    _description = 'Đăng ký học'
    _inherit = ['mail.thread']
    _order = 'date_enrolled desc'

    name = fields.Char(
        string='Mã đăng ký',
        required=True, copy=False, readonly=True,
        default=lambda self: _('New'),
    )
    student_id = fields.Many2one(
        comodel_name='edu.student',
        string='Học viên',
        required=True,
        ondelete='cascade',
        tracking=True,
    )
    class_id = fields.Many2one(
        comodel_name='edu.course.class',
        string='Lớp học',
        required=True,
        tracking=True,
    )
    course_id = fields.Many2one(
        comodel_name='edu.course',
        string='Khoá học',
        related='class_id.course_id',
        store=True,
    )
    admission_id = fields.Many2one(
        comodel_name='edu.admission',
        string='Hồ sơ tuyển sinh',
        ondelete='set null',
        copy=False,
        readonly=True,
        help='Hồ sơ tuyển sinh gốc (nếu có) – dùng để đồng bộ học phí/thanh toán '
             'từ Sales Order & Invoice. Để trống khi đăng ký trực tiếp không qua tuyển sinh.',
    )
    state = fields.Selection(
        selection=[
            ('registered', 'Đã đăng ký'),
            ('studying',   'Đang học'),
            ('on_leave',   'Bảo lưu'),
            ('completed',  'Hoàn thành'),
            ('failed',     'Không đạt'),
            ('cancelled',  'Huỷ'),
        ],
        string='Trạng thái',
        default='registered',
        tracking=True,
    )
    date_enrolled = fields.Date(string='Ngày đăng ký', default=fields.Date.today)
    date_start = fields.Date(string='Ngày bắt đầu học')
    date_end = fields.Date(string='Ngày kết thúc')

    tuition_fee = fields.Monetary(
        string='Học phí', currency_field='currency_id',
        compute='_compute_tuition_fee', store=True, readonly=False,
    )
    amount_paid = fields.Monetary(
        string='Đã đóng', currency_field='currency_id',
        compute='_compute_amount_paid', store=True, readonly=False,
    )
    payment_status = fields.Selection(
        selection=[
            ('unpaid',  'Chưa thanh toán'),
            ('partial', 'Thanh toán một phần'),
            ('paid',    'Đã thanh toán đủ'),
        ],
        string='Tình trạng thanh toán',
        compute='_compute_payment_status', store=True,
    )
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    note = fields.Text(string='Ghi chú')

    @api.depends('admission_id', 'admission_id.final_fee', 'class_id.course_id.tuition_fee')
    def _compute_tuition_fee(self):
        for rec in self:
            if rec.admission_id:
                rec.tuition_fee = rec.admission_id.final_fee
            elif not rec.tuition_fee:
                rec.tuition_fee = rec.class_id.course_id.tuition_fee or 0.0

    @api.depends('admission_id', 'admission_id.amount_paid')
    def _compute_amount_paid(self):
        for rec in self:
            if rec.admission_id:
                rec.amount_paid = rec.admission_id.amount_paid

    @api.depends('tuition_fee', 'amount_paid')
    def _compute_payment_status(self):
        for rec in self:
            if rec.amount_paid <= 0:
                rec.payment_status = 'unpaid'
            elif rec.tuition_fee and rec.amount_paid >= rec.tuition_fee:
                rec.payment_status = 'paid'
            else:
                rec.payment_status = 'partial'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('edu.enrollment') or _('New')
        return super().create(vals_list)
