# -*- coding: utf-8 -*-
"""
edu_parent.py
Quản lý thông tin phụ huynh / người bảo lãnh – quan hệ với học viên.
Quan trọng trong việc chăm sóc, thông báo và thu học phí cho học viên
là trẻ em hoặc phụ thuộc tài chính.
"""

from odoo import models, fields, api, _


class EduParent(models.Model):
    _name = 'edu.parent'
    _description = 'Phụ huynh / Người bảo lãnh'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'

    name = fields.Char(string='Họ và tên', required=True, tracking=True)
    relationship = fields.Selection(
        selection=[
            ('father',   'Bố'),
            ('mother',   'Mẹ'),
            ('sibling',  'Anh/Chị/Em'),
            ('spouse',   'Vợ/Chồng'),
            ('guardian', 'Người giám hộ'),
            ('employer', 'Công ty / Đơn vị bảo lãnh'),
            ('other',    'Khác'),
        ],
        string='Quan hệ với học viên',
        required=True,
    )
    student_id = fields.Many2one(
        comodel_name='edu.student',
        string='Học viên',
        required=True,
        ondelete='cascade',
        tracking=True,
    )

    # ── Liên lạc ─────────────────────────────────────────────────────────────
    phone = fields.Char(string='Số điện thoại', required=True, tracking=True)
    phone_other = fields.Char(string='Số điện thoại khác')
    email = fields.Char(string='Email', tracking=True)
    zalo = fields.Char(string='Zalo')
    facebook = fields.Char(string='Facebook')
    address = fields.Text(string='Địa chỉ')

    # ── Thông tin thêm ────────────────────────────────────────────────────────
    date_of_birth = fields.Date(string='Ngày sinh')
    id_number = fields.Char(string='CMND / CCCD')
    occupation = fields.Char(string='Nghề nghiệp')
    workplace = fields.Char(string='Nơi làm việc')

    # ── Vai trò thanh toán ────────────────────────────────────────────────────
    is_payer = fields.Boolean(
        string='Người thanh toán học phí',
        default=False,
        help='Đánh dấu nếu đây là người chịu trách nhiệm thanh toán học phí',
    )
    is_primary_contact = fields.Boolean(
        string='Đầu mối liên lạc chính',
        default=False,
    )

    # ── Liên kết Odoo partner ─────────────────────────────────────────────────
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Contact Odoo',
        ondelete='set null',
        help='Liên kết với res.partner để gửi email, tạo hóa đơn',
    )

    note = fields.Text(string='Ghi chú')

    # ── Compute display ───────────────────────────────────────────────────────
    display_name = fields.Char(
        string='Hiển thị',
        compute='_compute_display_name',
        store=True,
    )

    @api.depends('name', 'relationship', 'student_id.name')
    def _compute_display_name(self):
        for rec in self:
            rel_label = dict(rec._fields['relationship'].selection).get(rec.relationship, '')
            rec.display_name = f"{rec.name} ({rel_label}) – {rec.student_id.name or ''}"

    def action_send_sms(self):
        """Placeholder: gửi SMS/Zalo thông báo cho phụ huynh."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Gửi tin nhắn',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'target': 'new',
        }
