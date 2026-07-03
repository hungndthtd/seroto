# -*- coding: utf-8 -*-
"""
edu_certificate.py
Quản lý cấp phát chứng chỉ, bằng cấp cho học viên sau khi hoàn thành khoá học.
Hỗ trợ: chứng chỉ nội bộ, chứng chỉ quốc tế (IELTS, TOEIC, Cambridge…),
hoặc giấy khen, bảng điểm.
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import uuid


# ─────────────────────────────────────────────────────────────────────────────
# Mẫu chứng chỉ
# ─────────────────────────────────────────────────────────────────────────────
class EduCertificateTemplate(models.Model):
    _name = 'edu.certificate.template'
    _description = 'Mẫu chứng chỉ'
    _order = 'name asc'

    name = fields.Char(string='Tên mẫu chứng chỉ', required=True)
    certificate_type = fields.Selection(
        selection=[
            ('internal',     'Chứng chỉ nội bộ'),
            ('ielts',        'IELTS'),
            ('toeic',        'TOEIC'),
            ('cambridge',    'Cambridge (KET/PET/FCE…)'),
            ('toefl',        'TOEFL'),
            ('vstep',        'VSTEP (B1/B2/C1)'),
            ('transcript',   'Bảng điểm'),
            ('completion',   'Giấy hoàn thành khoá học'),
            ('other',        'Khác'),
        ],
        string='Loại chứng chỉ',
        required=True,
        default='internal',
    )
    description = fields.Text(string='Mô tả')
    template_html = fields.Html(string='Nội dung mẫu (HTML)')
    report_id = fields.Many2one(
        comodel_name='ir.actions.report',
        string='Mẫu in (Report)',
        ondelete='set null',
    )
    issuing_organization = fields.Char(
        string='Tổ chức cấp',
        default=lambda self: self.env.company.name,
    )
    validity_months = fields.Integer(
        string='Hiệu lực (tháng)',
        default=0,
        help='0 = vĩnh viễn',
    )
    active = fields.Boolean(default=True)
    course_ids = fields.Many2many(
        'edu.course',
        string='Khoá học áp dụng',
    )


# ─────────────────────────────────────────────────────────────────────────────
# Chứng chỉ cấp cho học viên
# ─────────────────────────────────────────────────────────────────────────────
class EduCertificate(models.Model):
    _name = 'edu.certificate'
    _description = 'Chứng chỉ học viên'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_issued desc'

    name = fields.Char(
        string='Số chứng chỉ',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ('draft',    'Nháp'),
            ('issued',   'Đã cấp'),
            ('revoked',  'Thu hồi'),
        ],
        string='Trạng thái',
        default='draft',
        tracking=True,
    )

    # ── Học viên & khoá học ────────────────────────────────────────────────
    student_id = fields.Many2one(
        'edu.student', string='Học viên', required=True, ondelete='restrict', tracking=True,
    )
    class_id = fields.Many2one(
        'edu.course.class', string='Lớp học', ondelete='set null', tracking=True,
    )
    course_id = fields.Many2one(
        'edu.course',
        string='Khoá học',
        related='class_id.course_id',
        store=True,
    )
    enrollment_id = fields.Many2one('edu.enrollment', string='Đăng ký học', ondelete='set null')

    # ── Loại & mẫu ────────────────────────────────────────────────────────
    template_id = fields.Many2one(
        'edu.certificate.template',
        string='Mẫu chứng chỉ',
        required=True,
        ondelete='restrict',
    )
    certificate_type = fields.Selection(
        related='template_id.certificate_type',
        store=True,
        string='Loại chứng chỉ',
    )
    issuing_organization = fields.Char(
        string='Tổ chức cấp',
        related='template_id.issuing_organization',
        store=True,
    )

    # ── Kết quả gắn với chứng chỉ ─────────────────────────────────────────
    exam_result_id = fields.Many2one(
        'edu.exam.result', string='Kết quả kỳ thi', ondelete='set null',
    )
    score = fields.Float(string='Điểm / Band score')
    grade = fields.Char(string='Xếp loại')
    skills_detail = fields.Text(
        string='Chi tiết kỹ năng (L/R/W/S)',
        help='VD: L: 7.0, R: 6.5, W: 6.0, S: 6.5',
    )

    # ── Ngày tháng ───────────────────────────────────────────────────────────
    date_issued = fields.Date(string='Ngày cấp', tracking=True)
    date_expiry = fields.Date(string='Ngày hết hạn', tracking=True)
    date_completed_course = fields.Date(string='Ngày hoàn thành khoá học')

    # ── Mã QR / xác minh ─────────────────────────────────────────────────────
    verification_code = fields.Char(
        string='Mã xác minh',
        copy=False,
        readonly=True,
        default=lambda self: str(uuid.uuid4()).replace('-', '').upper()[:12],
    )
    qr_code = fields.Binary(string='QR Code', attachment=True)

    # ── Người cấp ─────────────────────────────────────────────────────────────
    issued_by = fields.Many2one(
        'res.users', string='Người ký / Phê duyệt',
        default=lambda self: self.env.user,
    )

    # ── File chứng chỉ ────────────────────────────────────────────────────────
    certificate_file = fields.Binary(string='File chứng chỉ (PDF)', attachment=True)
    certificate_filename = fields.Char(string='Tên file')

    revoke_reason = fields.Text(string='Lý do thu hồi')
    note = fields.Text(string='Ghi chú')

    # ── Sequence ─────────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('edu.certificate') or _('New')
        return super().create(vals_list)

    # ── Actions ──────────────────────────────────────────────────────────────
    def action_issue(self):
        self.ensure_one()
        if not self.date_issued:
            self.date_issued = fields.Date.today()
        # Tính ngày hết hạn từ mẫu
        if self.template_id.validity_months:
            from dateutil.relativedelta import relativedelta
            self.date_expiry = self.date_issued + relativedelta(months=self.template_id.validity_months)
        self.write({'state': 'issued'})
        self.message_post(body=_('Chứng chỉ đã được cấp cho %s.') % self.student_id.name)

    def action_revoke(self):
        self.write({'state': 'revoked'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})

    def action_print_certificate(self):
        """In chứng chỉ qua report template."""
        if self.template_id.report_id:
            return self.template_id.report_id.report_action(self)
        raise ValidationError(_('Chưa cấu hình mẫu in cho loại chứng chỉ này.'))

    # ── Constraints ──────────────────────────────────────────────────────────
    @api.constrains('date_issued', 'date_expiry')
    def _check_dates(self):
        for rec in self:
            if rec.date_issued and rec.date_expiry and rec.date_expiry < rec.date_issued:
                raise ValidationError(_('Ngày hết hạn phải sau ngày cấp.'))

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Số chứng chỉ phải là duy nhất!'),
    ]
