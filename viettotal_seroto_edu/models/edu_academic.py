# -*- coding: utf-8 -*-
"""
edu_academic.py
Cấu trúc học thuật: Khoá học (Course) → Lớp học (Class) → Buổi học (Session).

Khoá học liên kết với product.template (type=service) để:
  - Dùng trong sale.order.line → tạo Sales Order / Invoice native
  - Quản lý giá theo pricelist, thuế VAT
  - Báo cáo doanh thu Odoo tự tổng hợp

Khi tạo edu.course, hệ thống tự tạo product.template tương ứng.
Khi cập nhật tên / giá / mô tả → đồng bộ sang product tự động.
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


# ─────────────────────────────────────────────────────────────────────────────
# Danh mục khoá học
# ─────────────────────────────────────────────────────────────────────────────
class EduCourseCategory(models.Model):
    _name = 'edu.course.category'
    _description = 'Danh mục khoá học'
    _order = 'sequence, name'

    name = fields.Char(string='Tên danh mục', required=True)
    sequence = fields.Integer(default=10)
    parent_id = fields.Many2one('edu.course.category', string='Danh mục cha', ondelete='set null')
    child_ids = fields.One2many('edu.course.category', 'parent_id', string='Danh mục con')
    description = fields.Text(string='Mô tả')
    active = fields.Boolean(default=True)


# ─────────────────────────────────────────────────────────────────────────────
# Khoá học – liên kết product.template
# ─────────────────────────────────────────────────────────────────────────────
class EduCourse(models.Model):
    _name = 'edu.course'
    _description = 'Khoá học'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'

    name = fields.Char(string='Tên khoá học', required=True, tracking=True)
    code = fields.Char(string='Mã khoá học', required=True, copy=False)
    category_id = fields.Many2one('edu.course.category', string='Danh mục')
    active = fields.Boolean(default=True)
    state = fields.Selection(
        selection=[
            ('draft',     'Nháp'),
            ('published', 'Đang mở đăng ký'),
            ('closed',    'Đóng đăng ký'),
            ('archived',  'Lưu trữ'),
        ],
        string='Trạng thái',
        default='draft',
        tracking=True,
    )

    # ── Mô tả & Nội dung ─────────────────────────────────────────────────────
    description = fields.Html(string='Mô tả khoá học')
    target_audience = fields.Text(string='Đối tượng học viên')
    objectives = fields.Text(string='Mục tiêu khoá học / Đầu ra')
    prerequisites = fields.Text(string='Yêu cầu đầu vào')

    # ── Thời lượng ───────────────────────────────────────────────────────────
    total_sessions = fields.Integer(string='Tổng số buổi học')
    session_duration = fields.Float(string='Thời lượng mỗi buổi (giờ)', default=2.0)
    total_hours = fields.Float(
        string='Tổng số giờ',
        compute='_compute_total_hours',
        store=True,
    )

    # ── Học phí – đồng bộ 2 chiều với product.template ──────────────────────
    tuition_fee = fields.Monetary(
        string='Học phí niêm yết',
        currency_field='currency_id',
        tracking=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )

    # ── Thuế bán hàng (lấy từ product, hiển thị để cấu hình) ────────────────
    tax_ids = fields.Many2many(
        comodel_name='account.tax',
        string='Thuế bán hàng',
        domain=[('type_tax_use', '=', 'sale')],
        help='Thuế sẽ áp dụng khi tạo Sales Order / Invoice',
    )

    # ── Liên kết product.template ─────────────────────────────────────────────
    product_id = fields.Many2one(
        comodel_name='product.template',
        string='Sản phẩm dịch vụ',
        ondelete='restrict',
        copy=False,
        readonly=True,
        help='Product tương ứng dùng trong Sales Order và Invoice. '
             'Tự động tạo khi lưu khoá học lần đầu.',
    )
    product_variant_id = fields.Many2one(
        comodel_name='product.product',
        string='Product Variant',
        compute='_compute_product_variant',
        store=True,
        help='Variant mặc định dùng trong sale.order.line',
    )

    # ── Chứng chỉ đầu ra ─────────────────────────────────────────────────────
    certificate_type = fields.Char(string='Loại chứng chỉ (IELTS, TOEIC, nội bộ…)')
    has_certificate = fields.Boolean(string='Cấp chứng chỉ khi hoàn thành')

    # ── Lớp học ──────────────────────────────────────────────────────────────
    class_ids = fields.One2many('edu.course.class', 'course_id', string='Danh sách lớp')
    class_count = fields.Integer(compute='_compute_class_count', string='Số lớp')

    image = fields.Image(string='Ảnh khoá học', max_width=512, max_height=512)
    note = fields.Text(string='Ghi chú nội bộ')

    # ── Compute ──────────────────────────────────────────────────────────────
    @api.depends('total_sessions', 'session_duration')
    def _compute_total_hours(self):
        for rec in self:
            rec.total_hours = (rec.total_sessions or 0) * (rec.session_duration or 0)

    @api.depends('class_ids')
    def _compute_class_count(self):
        for rec in self:
            rec.class_count = len(rec.class_ids)

    @api.depends('product_id')
    def _compute_product_variant(self):
        for rec in self:
            if rec.product_id:
                rec.product_variant_id = rec.product_id.product_variant_id
            else:
                rec.product_variant_id = False

    # ── Tạo / đồng bộ product.template ──────────────────────────────────────
    def _prepare_product_vals(self):
        """Giá trị để tạo hoặc cập nhật product.template."""
        return {
            'name':             self.name,
            'type':             'service',          # Dịch vụ – không theo dõi tồn kho
            'invoice_policy':   'order',            # Xuất hoá đơn ngay khi đặt hàng
            'sale_ok':          True,
            'purchase_ok':      False,              # Khoá học chỉ bán, không mua
            'list_price':       self.tuition_fee or 0.0,
            'taxes_id':         [(6, 0, self.tax_ids.ids)],
            'description_sale': self.objectives or '',
            'active':           self.active,
            # Tag để dễ lọc trong product list
            'categ_id':         self.env.ref('product.product_category_services').id,
        }

    def _sync_product(self):
        """Tạo product nếu chưa có, cập nhật nếu đã có."""
        ProductTmpl = self.env['product.template']
        for rec in self:
            vals = rec._prepare_product_vals()
            if not rec.product_id:
                # Thêm internal_ref = mã khoá học
                vals['default_code'] = rec.code
                product = ProductTmpl.create(vals)
                rec.product_id = product.id
            else:
                rec.product_id.write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_product()
        return records

    def write(self, vals):
        result = super().write(vals)
        # Đồng bộ khi các field ảnh hưởng product thay đổi
        sync_triggers = {'name', 'tuition_fee', 'objectives', 'active', 'tax_ids'}
        if sync_triggers & set(vals.keys()):
            self._sync_product()
        return result

    # ── Actions ──────────────────────────────────────────────────────────────
    def action_view_classes(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Lớp của {self.name}',
            'res_model': 'edu.course.class',
            'view_mode': 'list,form',
            'domain': [('course_id', '=', self.id)],
        }

    def action_view_product(self):
        """Mở product.template liên kết."""
        self.ensure_one()
        if not self.product_id:
            self._sync_product()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Sản phẩm – {self.name}',
            'res_model': 'product.template',
            'res_id': self.product_id.id,
            'view_mode': 'form',
        }

    def action_publish(self):
        self.write({'state': 'published'})

    def action_close(self):
        self.write({'state': 'closed'})

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Mã khoá học phải là duy nhất!'),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Phòng học
# ─────────────────────────────────────────────────────────────────────────────
class EduRoom(models.Model):
    _name = 'edu.room'
    _description = 'Phòng học / Cơ sở'

    name = fields.Char(string='Tên phòng / địa điểm', required=True)
    capacity = fields.Integer(string='Sức chứa (học viên)')
    location = fields.Char(string='Địa chỉ / Cơ sở')
    room_type = fields.Selection(
        selection=[
            ('classroom', 'Phòng học'),
            ('lab',       'Phòng thực hành'),
            ('online',    'Trực tuyến (Online)'),
        ],
        string='Loại phòng',
        default='classroom',
    )
    active = fields.Boolean(default=True)
    note = fields.Text(string='Ghi chú')


# ─────────────────────────────────────────────────────────────────────────────
# Lớp học
# ─────────────────────────────────────────────────────────────────────────────
class EduCourseClass(models.Model):
    _name = 'edu.course.class'
    _description = 'Lớp học'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, name asc'

    name = fields.Char(string='Tên lớp', required=True, tracking=True)
    code = fields.Char(string='Mã lớp', required=True, copy=False)
    course_id = fields.Many2one(
        'edu.course', string='Khoá học',
        required=True, ondelete='restrict', tracking=True,
    )
    teacher_id = fields.Many2one('edu.teacher', string='Giáo viên phụ trách', tracking=True)
    room_id = fields.Many2one('edu.room', string='Phòng học / Hình thức')
    state = fields.Selection(
        selection=[
            ('scheduled', 'Chờ khai giảng'),
            ('ongoing',   'Đang học'),
            ('completed', 'Đã kết thúc'),
            ('cancelled', 'Huỷ'),
        ],
        string='Trạng thái lớp',
        default='scheduled',
        tracking=True,
    )

    date_start = fields.Date(string='Ngày khai giảng', tracking=True)
    date_end = fields.Date(string='Ngày kết thúc dự kiến', tracking=True)
    schedule_note = fields.Text(string='Lịch học', help='VD: Thứ 2-4-6, 18:00–20:00')

    max_students = fields.Integer(string='Sĩ số tối đa', default=20)
    enrollment_ids = fields.One2many('edu.enrollment', 'class_id', string='Danh sách học viên')
    enrolled_count = fields.Integer(
        string='Số học viên đã đăng ký',
        compute='_compute_enrolled_count',
        store=True,
    )
    available_seats = fields.Integer(
        string='Chỗ còn trống',
        compute='_compute_available_seats',
        store=True,
    )

    session_ids = fields.One2many('edu.session', 'class_id', string='Danh sách buổi học')
    session_count = fields.Integer(compute='_compute_session_count', string='Số buổi')

    note = fields.Text(string='Ghi chú')

    @api.depends('enrollment_ids', 'enrollment_ids.state')
    def _compute_enrolled_count(self):
        for rec in self:
            rec.enrolled_count = len(rec.enrollment_ids.filtered(
                lambda e: e.state not in ('cancelled',)
            ))

    @api.depends('max_students', 'enrolled_count')
    def _compute_available_seats(self):
        for rec in self:
            rec.available_seats = max(0, (rec.max_students or 0) - rec.enrolled_count)

    @api.depends('session_ids')
    def _compute_session_count(self):
        for rec in self:
            rec.session_count = len(rec.session_ids)

    def action_start_class(self):
        self.write({'state': 'ongoing'})

    def action_complete_class(self):
        self.write({'state': 'completed'})

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Mã lớp phải là duy nhất!'),
    ]

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_end < rec.date_start:
                raise ValidationError(_('Ngày kết thúc phải sau ngày khai giảng.'))


# ─────────────────────────────────────────────────────────────────────────────
# Buổi học
# ─────────────────────────────────────────────────────────────────────────────
class EduSession(models.Model):
    _name = 'edu.session'
    _description = 'Buổi học'
    _order = 'date_session asc, sequence asc'

    name = fields.Char(string='Tên buổi học', required=True)
    sequence = fields.Integer(string='Thứ tự buổi', default=1)
    class_id = fields.Many2one('edu.course.class', string='Lớp học', required=True, ondelete='cascade')
    teacher_id = fields.Many2one(
        'edu.teacher', string='Giáo viên',
        related='class_id.teacher_id', store=True,
    )
    room_id = fields.Many2one('edu.room', string='Phòng học')

    date_session = fields.Date(string='Ngày học', required=True)
    time_start = fields.Float(string='Giờ bắt đầu', help='VD: 18.0 = 18:00')
    time_end = fields.Float(string='Giờ kết thúc')
    duration = fields.Float(string='Thời lượng (giờ)', compute='_compute_duration', store=True)

    topic = fields.Char(string='Chủ đề / Nội dung buổi học')
    description = fields.Text(string='Mô tả chi tiết')
    homework = fields.Text(string='Bài tập về nhà')

    state = fields.Selection(
        selection=[
            ('planned',   'Chờ học'),
            ('completed', 'Đã học'),
            ('cancelled', 'Huỷ / Nghỉ'),
            ('postponed', 'Dời lịch'),
        ],
        string='Trạng thái',
        default='planned',
    )
    cancel_reason = fields.Text(string='Lý do huỷ / dời')
    attendance_ids = fields.One2many('edu.attendance', 'session_id', string='Điểm danh')

    @api.depends('time_start', 'time_end')
    def _compute_duration(self):
        for rec in self:
            rec.duration = max(0.0, rec.time_end - rec.time_start)
