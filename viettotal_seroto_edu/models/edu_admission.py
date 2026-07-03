# -*- coding: utf-8 -*-
"""
edu_admission.py
Quản lý quá trình tuyển sinh: Lead → Tư vấn → Đăng ký → Hợp đồng → Thanh toán → Nhập học.

Luồng Sales tích hợp:
  action_create_sale_order() → tạo sale.order với course product
  action_view_invoice()      → xem hoá đơn từ sale.order
  Payment status             → đồng bộ từ sale.order / account.move

Luồng đầy đủ:
  WEBSITE → crm.lead → edu.admission → sale.order → account.move (Invoice)
                                              ↓
                                       edu.student (sau khi paid/enrolled)
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class EduAdmission(models.Model):
    _name = 'edu.admission'
    _description = 'Hồ sơ tuyển sinh'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_registration desc, id desc'

    # ── Thông tin cơ bản ─────────────────────────────────────────────────────
    name = fields.Char(
        string='Mã hồ sơ', required=True, copy=False,
        readonly=True, default=lambda self: _('New'), tracking=True,
    )
    state = fields.Selection(
        selection=[
            ('new',        'Mới tiếp nhận'),
            ('consulting', 'Đang tư vấn'),
            ('registered', 'Đã đăng ký'),
            ('contracted', 'Đã ký hợp đồng'),
            ('paid',       'Đã thanh toán'),
            ('enrolled',   'Đã nhập học'),
            ('cancelled',  'Huỷ'),
        ],
        string='Trạng thái', default='new', required=True, tracking=True,
    )

    # ── Liên kết CRM ─────────────────────────────────────────────────────────
    crm_lead_id = fields.Many2one(
        'crm.lead', string='Lead CRM', ondelete='set null', tracking=True,
    )
    partner_id = fields.Many2one(
        'res.partner', string='Người liên hệ (Contact)', required=True, tracking=True,
    )

    # ── Liên kết Sales & Invoice ─────────────────────────────────────────────
    sale_order_id = fields.Many2one(
        'sale.order', string='Sales Order', ondelete='set null',
        readonly=True, copy=False, tracking=True,
    )
    sale_order_state = fields.Selection(
        related='sale_order_id.state', string='Trạng thái SO', store=True,
    )
    invoice_ids = fields.Many2many(
        comodel_name='account.move',
        string='Hoá đơn',
        compute='_compute_invoice_ids',
        store=False,
    )
    invoice_count = fields.Integer(
        string='Số hoá đơn', compute='_compute_invoice_ids',
    )
    invoice_payment_state = fields.Char(
        string='Trạng thái thanh toán HĐ',
        compute='_compute_invoice_ids',
    )

    # ── Thông tin học viên ───────────────────────────────────────────────────
    student_name = fields.Char(string='Họ và tên học viên', required=True, tracking=True)
    date_of_birth = fields.Date(string='Ngày sinh', tracking=True)
    gender = fields.Selection(
        [('male', 'Nam'), ('female', 'Nữ'), ('other', 'Khác')], string='Giới tính',
    )
    phone = fields.Char(string='Số điện thoại', tracking=True)
    email = fields.Char(string='Email', tracking=True)
    id_number = fields.Char(string='CMND / CCCD', tracking=True)
    address = fields.Text(string='Địa chỉ thường trú')
    current_address = fields.Text(string='Địa chỉ hiện tại')

    # ── Học vấn & Mục tiêu (thu thập từ form đăng ký) ────────────────────────
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
    current_job = fields.Char(string='Nghề nghiệp hiện tại')
    workplace = fields.Char(string='Nơi làm việc')
    learning_goal = fields.Text(string='Mục tiêu học tập')
    english_level = fields.Selection(
        selection=[
            ('beginner',           'Mất gốc / Mới bắt đầu'),
            ('elementary',         'Sơ cấp'),
            ('pre_intermediate',   'Trung cấp thấp'),
            ('intermediate',       'Trung cấp'),
            ('upper_intermediate', 'Trung cấp cao'),
            ('advanced',           'Nâng cao'),
        ],
        string='Trình độ tiếng Anh đầu vào',
    )
    target_cert = fields.Char(string='Chứng chỉ mục tiêu (IELTS, TOEIC…)')
    target_score = fields.Float(string='Điểm mục tiêu')

    # ── Phụ huynh ────────────────────────────────────────────────────────────
    parent_name = fields.Char(string='Họ tên phụ huynh / bảo lãnh')
    parent_phone = fields.Char(string='SĐT phụ huynh')
    parent_relationship = fields.Selection(
        [('father','Bố'),('mother','Mẹ'),('sibling','Anh/Chị/Em'),
         ('guardian','Người bảo lãnh'),('other','Khác')],
        string='Quan hệ với học viên',
    )

    # ── Khoá học ─────────────────────────────────────────────────────────────
    course_id = fields.Many2one('edu.course', string='Khoá học', tracking=True)
    course_class_id = fields.Many2one(
        'edu.course.class', string='Lớp học dự kiến',
        domain="[('course_id','=',course_id)]", tracking=True,
    )
    date_registration = fields.Date(
        string='Ngày đăng ký', default=fields.Date.today, tracking=True,
    )
    expected_start_date = fields.Date(string='Ngày dự kiến nhập học', tracking=True)

    # ── Nguồn tuyển sinh ─────────────────────────────────────────────────────
    source_id = fields.Many2one('utm.source', string='Nguồn (UTM Source)')
    medium_id = fields.Many2one('utm.medium', string='Kênh (UTM Medium)')
    campaign_id = fields.Many2one('utm.campaign', string='Chiến dịch')
    admission_channel = fields.Selection(
        [('website','Website'),('facebook','Facebook'),('zalo','Zalo'),
         ('referral','Giới thiệu'),('telesales','Telesales'),
         ('walk_in','Đến trực tiếp'),('other','Khác')],
        string='Kênh tuyển sinh', tracking=True,
    )
    referred_by = fields.Char(string='Được giới thiệu bởi')
    counselor_id = fields.Many2one(
        'res.users', string='Tư vấn viên',
        default=lambda self: self.env.user, tracking=True,
    )

    # ── Học phí ──────────────────────────────────────────────────────────────
    tuition_fee = fields.Monetary(
        string='Học phí niêm yết', currency_field='currency_id',
        compute='_compute_tuition_fee', store=True, readonly=False,
    )
    discount_amount = fields.Monetary(string='Giảm giá', currency_field='currency_id')
    discount_reason = fields.Char(string='Lý do giảm giá')
    final_fee = fields.Monetary(
        string='Học phí thực thu', compute='_compute_final_fee',
        store=True, currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id,
    )

    # ── Trạng thái thanh toán (từ SO/Invoice) ────────────────────────────────
    payment_status = fields.Selection(
        [('unpaid','Chưa thanh toán'),('partial','Thanh toán một phần'),('paid','Đã thanh toán đủ')],
        string='Tình trạng thanh toán', default='unpaid', tracking=True,
    )
    amount_paid = fields.Monetary(
        string='Đã thanh toán', currency_field='currency_id',
        compute='_compute_amount_paid', store=True,
    )
    amount_remaining = fields.Monetary(
        string='Còn lại', compute='_compute_amount_remaining',
        store=True, currency_field='currency_id',
    )

    # ── Ghi chú ──────────────────────────────────────────────────────────────
    note = fields.Text(string='Ghi chú tư vấn')
    cancel_reason = fields.Text(string='Lý do huỷ')

    # ── Học viên ─────────────────────────────────────────────────────────────
    student_id = fields.Many2one(
        'edu.student', string='Học viên', readonly=True, copy=False, tracking=True,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Compute
    # ─────────────────────────────────────────────────────────────────────────
    @api.depends('course_id', 'course_id.tuition_fee')
    def _compute_tuition_fee(self):
        for rec in self:
            if rec.course_id and not rec.tuition_fee:
                rec.tuition_fee = rec.course_id.tuition_fee

    @api.depends('tuition_fee', 'discount_amount')
    def _compute_final_fee(self):
        for rec in self:
            rec.final_fee = (rec.tuition_fee or 0.0) - (rec.discount_amount or 0.0)

    @api.depends('sale_order_id', 'sale_order_id.invoice_ids.amount_residual',
                 'sale_order_id.invoice_ids.payment_state')
    def _compute_invoice_ids(self):
        for rec in self:
            if rec.sale_order_id:
                invoices = rec.sale_order_id.invoice_ids
                rec.invoice_ids = invoices
                rec.invoice_count = len(invoices)
                # Tổng hợp trạng thái thanh toán
                states = invoices.mapped('payment_state')
                if all(s == 'paid' for s in states) and states:
                    rec.invoice_payment_state = 'paid'
                elif any(s in ('partial', 'paid') for s in states):
                    rec.invoice_payment_state = 'partial'
                else:
                    rec.invoice_payment_state = 'not_paid'
            else:
                rec.invoice_ids = False
                rec.invoice_count = 0
                rec.invoice_payment_state = 'not_paid'

    @api.depends('sale_order_id', 'sale_order_id.invoice_ids.amount_residual',
                 'sale_order_id.invoice_ids.payment_state',
                 'sale_order_id.invoice_ids.amount_total')
    def _compute_amount_paid(self):
        for rec in self:
            if rec.sale_order_id:
                invoices = rec.sale_order_id.invoice_ids.filtered(
                    lambda inv: inv.state == 'posted' and inv.move_type == 'out_invoice'
                )
                total = sum(invoices.mapped('amount_total'))
                residual = sum(invoices.mapped('amount_residual'))
                rec.amount_paid = total - residual
            else:
                rec.amount_paid = 0.0

    @api.depends('final_fee', 'amount_paid')
    def _compute_amount_remaining(self):
        for rec in self:
            rec.amount_remaining = max(0.0, (rec.final_fee or 0.0) - (rec.amount_paid or 0.0))

    # ─────────────────────────────────────────────────────────────────────────
    # Sequence
    # ─────────────────────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('edu.admission') or _('New')
        return super().create(vals_list)

    # ─────────────────────────────────────────────────────────────────────────
    # onchange: khi đổi khoá học → gợi ý học phí
    # ─────────────────────────────────────────────────────────────────────────
    @api.onchange('course_id')
    def _onchange_course_id(self):
        if self.course_id:
            self.tuition_fee = self.course_id.tuition_fee
            self.course_class_id = False  # reset lớp khi đổi khoá

    # ─────────────────────────────────────────────────────────────────────────
    # Actions – Workflow
    # ─────────────────────────────────────────────────────────────────────────
    def action_confirm_registration(self):
        self.write({'state': 'registered'})

    def action_sign_contract(self):
        """Ký hợp đồng → tự tạo Sales Order nếu chưa có."""
        self.ensure_one()
        if not self.sale_order_id:
            self._create_sale_order()
        self.write({'state': 'contracted'})

    def action_confirm_payment(self):
        """Xác nhận đã thanh toán thủ công (dùng khi không qua SO)."""
        self.write({'state': 'paid', 'payment_status': 'paid'})

    def action_enroll(self):
        """Tạo edu.student + gắn vào lớp học."""
        self.ensure_one()
        if not self.student_id:
            student = self.env['edu.student'].create({
                'name':          self.student_name,
                'date_of_birth': self.date_of_birth,
                'gender':        self.gender,
                'phone':         self.phone,
                'email':         self.email,
                'id_number':     self.id_number,
                'address':       self.address,
                'education_level': self.education_level,
                'current_job':   self.current_job,
                'workplace':     self.workplace,
                'learning_goal': self.learning_goal,
                'english_level': self.english_level,
                'target_cert':   self.target_cert,
                'target_score':  self.target_score,
                'partner_id':    self.partner_id.id,
                'admission_id':  self.id,
                'counselor_id':  self.counselor_id.id,
                'date_enrollment': fields.Date.today(),
            })
            self.student_id = student.id

            # Tạo enrollment vào lớp nếu đã chọn
            # tuition_fee/amount_paid sẽ tự tính từ admission_id (xem edu.enrollment)
            if self.course_class_id:
                self.env['edu.enrollment'].create({
                    'student_id':    student.id,
                    'class_id':      self.course_class_id.id,
                    'admission_id':  self.id,
                    'date_enrolled': fields.Date.today(),
                    'state':         'studying',
                })

        self.write({'state': 'enrolled'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'edu.student',
            'res_id': self.student_id.id,
            'view_mode': 'form',
        }

    def action_cancel(self):
        """Huỷ hồ sơ – huỷ SO nếu chưa có invoice."""
        for rec in self:
            if rec.sale_order_id and rec.sale_order_id.state not in ('cancel', 'done'):
                if rec.invoice_count == 0:
                    rec.sale_order_id.action_cancel()
        self.write({'state': 'cancelled'})

    def action_reset_to_new(self):
        self.write({'state': 'new'})

    # ─────────────────────────────────────────────────────────────────────────
    # Actions – Sales & Invoice
    # ─────────────────────────────────────────────────────────────────────────
    def action_create_sale_order(self):
        """Tạo Sales Order từ hồ sơ tuyển sinh (gọi thủ công)."""
        self.ensure_one()
        if self.sale_order_id:
            raise UserError(_('Hồ sơ này đã có Sales Order: %s') % self.sale_order_id.name)
        self._create_sale_order()
        return self.action_view_sale_order()

    def _create_sale_order(self):
        """
        Tạo sale.order với 1 order line = product của khoá học.
        - Nếu course chưa có product → tự tạo qua _sync_product()
        - Giá = final_fee (đã trừ giảm giá)
        - Ghi chú SO = mã hồ sơ + lớp học
        """
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_('Vui lòng chọn Người liên hệ trước khi tạo Sales Order.'))
        if not self.course_id:
            raise UserError(_('Vui lòng chọn Khoá học trước khi tạo Sales Order.'))

        # Đảm bảo course có product
        if not self.course_id.product_id:
            self.course_id._sync_product()

        product_variant = self.course_id.product_variant_id
        if not product_variant:
            raise UserError(_(
                'Khoá học "%s" chưa có sản phẩm liên kết. '
                'Vui lòng lưu khoá học lại để hệ thống tạo sản phẩm tự động.'
            ) % self.course_id.name)

        # Tên ghi chú trên SO
        so_note_parts = [f'Hồ sơ: {self.name}']
        if self.course_class_id:
            so_note_parts.append(f'Lớp: {self.course_class_id.name}')
        if self.admission_channel:
            channel_label = dict(
                self._fields['admission_channel'].selection
            ).get(self.admission_channel, '')
            so_note_parts.append(f'Kênh: {channel_label}')

        # Tỷ lệ giảm giá (%)
        discount_pct = 0.0
        if self.tuition_fee and self.discount_amount:
            discount_pct = (self.discount_amount / self.tuition_fee) * 100

        order_line_vals = {
            'product_id':    product_variant.id,
            'product_uom_qty': 1.0,
            'price_unit':    self.tuition_fee or 0.0,
            'discount':      discount_pct,
            'name':          self.course_id.name + (
                f'\n{self.course_class_id.name}' if self.course_class_id else ''
            ),
            'tax_ids':       [(6, 0, self.course_id.tax_ids.ids)],
        }

        so_vals = {
            'partner_id':    self.partner_id.id,
            'origin':        self.name,
            'note':          '\n'.join(so_note_parts),
            'order_line':    [(0, 0, order_line_vals)],
            'source_id':     self.source_id.id or False,
            'medium_id':     self.medium_id.id or False,
            'campaign_id':   self.campaign_id.id or False,
        }

        so = self.env['sale.order'].create(so_vals)
        so.action_confirm()  # Confirm ngay để tạo được invoice
        self.sale_order_id = so.id

        self.message_post(body=_(
            'Đã tạo Sales Order <a href="/web#id=%(so_id)s&model=sale.order">%(so_name)s</a>.',
            so_id=so.id, so_name=so.name,
        ))
        return so

    def action_view_sale_order(self):
        """Mở Sales Order liên kết."""
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError(_('Chưa có Sales Order. Vui lòng tạo trước.'))
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales Order',
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
        }

    def action_view_invoice(self):
        """Mở danh sách hoá đơn của hồ sơ."""
        self.ensure_one()
        invoices = self.sale_order_id.invoice_ids if self.sale_order_id else self.env['account.move']
        if not invoices:
            raise UserError(_('Chưa có hoá đơn nào. Vui lòng tạo hoá đơn từ Sales Order.'))
        action = {
            'type': 'ir.actions.act_window',
            'name': f'Hoá đơn – {self.student_name}',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', invoices.ids)],
        }
        if len(invoices) == 1:
            action.update({'view_mode': 'form', 'res_id': invoices.id})
        return action

    def action_create_invoice(self):
        """Tạo hoá đơn từ Sales Order (shortcut)."""
        self.ensure_one()
        if not self.sale_order_id:
            self._create_sale_order()
        return self.sale_order_id._create_invoices()

    # ─────────────────────────────────────────────────────────────────────────
    # Constraints
    # ─────────────────────────────────────────────────────────────────────────
    @api.constrains('tuition_fee', 'discount_amount')
    def _check_discount(self):
        for rec in self:
            if rec.discount_amount and rec.tuition_fee and rec.discount_amount > rec.tuition_fee:
                raise ValidationError(_('Giảm giá không được lớn hơn học phí.'))
