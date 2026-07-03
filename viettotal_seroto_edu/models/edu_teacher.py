# -*- coding: utf-8 -*-
"""
edu_teacher.py
Quản lý giáo viên / giảng viên: hồ sơ, lịch dạy, lớp phụ trách.
"""

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta


class EduTeacher(models.Model):
    _name = 'edu.teacher'
    _description = 'Giáo viên / Giảng viên'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'

    # ── Định danh ────────────────────────────────────────────────────────────
    name = fields.Char(string='Họ và tên', required=True, tracking=True)
    teacher_code = fields.Char(
        string='Mã giáo viên',
        required=True, copy=False, readonly=True,
        default=lambda self: _('New'),
    )
    active = fields.Boolean(default=True, string='Đang làm việc')
    state = fields.Selection(
        selection=[
            ('probation',  'Thử việc'),
            ('official',   'Chính thức'),
            ('part_time',  'Bán thời gian'),
            ('resigned',   'Đã nghỉ việc'),
        ],
        string='Trạng thái hợp đồng',
        default='official',
        tracking=True,
    )

    # ── Thông tin cá nhân ────────────────────────────────────────────────────
    date_of_birth = fields.Date(string='Ngày sinh')
    age = fields.Integer(string='Tuổi', compute='_compute_age')
    gender = fields.Selection(
        selection=[('male', 'Nam'), ('female', 'Nữ'), ('other', 'Khác')],
        string='Giới tính',
    )
    id_number = fields.Char(string='CMND / CCCD')
    nationality_id = fields.Many2one('res.country', string='Quốc tịch')
    phone = fields.Char(string='Số điện thoại', tracking=True)
    email = fields.Char(string='Email', tracking=True)
    address = fields.Text(string='Địa chỉ')
    image = fields.Image(string='Ảnh', max_width=256, max_height=256)

    # ── Chuyên môn ───────────────────────────────────────────────────────────
    specialization = fields.Char(string='Chuyên môn / Môn dạy')
    degree = fields.Selection(
        selection=[
            ('college',      'Cao đẳng'),
            ('bachelor',     'Cử nhân'),
            ('master',       'Thạc sĩ'),
            ('phd',          'Tiến sĩ'),
            ('native',       'Bản ngữ'),
            ('other',        'Khác'),
        ],
        string='Bằng cấp cao nhất',
    )
    degree_major = fields.Char(string='Chuyên ngành bằng cấp')
    years_experience = fields.Integer(string='Số năm kinh nghiệm')
    certificate_ids = fields.One2many(
        comodel_name='edu.teacher.certificate',
        inverse_name='teacher_id',
        string='Chứng chỉ / Bằng cấp',
    )

    # ── Lịch dạy & Lớp phụ trách ─────────────────────────────────────────────
    class_ids = fields.One2many(
        comodel_name='edu.course.class',
        inverse_name='teacher_id',
        string='Lớp phụ trách',
    )
    class_count = fields.Integer(
        string='Số lớp',
        compute='_compute_class_count',
    )

    # ── Nhân sự Odoo ─────────────────────────────────────────────────────────
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Tài khoản người dùng',
        ondelete='set null',
    )
    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Hồ sơ nhân viên (HR)',
        ondelete='set null',
    )

    # ── Lương / Hoa hồng ─────────────────────────────────────────────────────
    salary_type = fields.Selection(
        selection=[
            ('fixed',      'Cố định'),
            ('per_session', 'Theo buổi'),
            ('per_student', 'Theo học viên'),
        ],
        string='Loại lương',
        default='per_session',
    )
    salary_rate = fields.Float(string='Mức lương / tỷ lệ')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    note = fields.Text(string='Ghi chú')

    # ── Compute ──────────────────────────────────────────────────────────────
    @api.depends('date_of_birth')
    def _compute_age(self):
        today = fields.Date.today()
        for rec in self:
            rec.age = relativedelta(today, rec.date_of_birth).years if rec.date_of_birth else 0

    @api.depends('class_ids')
    def _compute_class_count(self):
        for rec in self:
            rec.class_count = len(rec.class_ids)

    # ── Sequence ─────────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('teacher_code', _('New')) == _('New'):
                vals['teacher_code'] = self.env['ir.sequence'].next_by_code('edu.teacher') or _('New')
        return super().create(vals_list)

    # ── Actions ──────────────────────────────────────────────────────────────
    def action_view_classes(self):
        return {
            'type': 'ir.actions.act_window',
            'name': f'Lớp của {self.name}',
            'res_model': 'edu.course.class',
            'view_mode': 'list,form',
            'domain': [('teacher_id', '=', self.id)],
        }

    _sql_constraints = [
        ('teacher_code_unique', 'unique(teacher_code)', 'Mã giáo viên phải là duy nhất!'),
    ]


class EduTeacherCertificate(models.Model):
    _name = 'edu.teacher.certificate'
    _description = 'Chứng chỉ / Bằng cấp giáo viên'

    teacher_id = fields.Many2one('edu.teacher', string='Giáo viên', required=True, ondelete='cascade')
    name = fields.Char(string='Tên chứng chỉ / bằng cấp', required=True)
    issuer = fields.Char(string='Tổ chức cấp')
    issue_date = fields.Date(string='Ngày cấp')
    expiry_date = fields.Date(string='Ngày hết hạn')
    score = fields.Float(string='Điểm số / Band score')
    attachment_id = fields.Many2one('ir.attachment', string='File đính kèm')
    note = fields.Text(string='Ghi chú')
