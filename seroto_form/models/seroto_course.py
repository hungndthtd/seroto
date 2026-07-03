from odoo import models, fields, api, _

# ---
# Đối tượng khóa học (tag) - vd: Giáo viên, Học viên
# Dùng để 1 khóa học có thể hiển thị đồng thời ở nhiều đề mục trên website
# (xem seroto.course.audience_ids bên dưới và views/snippets/s_course_card.xml).
# Tạo thủ công qua menu Khoá học > Đối tượng khóa học - không cài sẵn dữ liệu mẫu.
# ---

class SerotoCourseAudience(models.Model):
  _name = 'seroto.course.audience'
  _description = 'Đối tượng khóa học'
  _order = 'sequence, name'

  name = fields.Char(string='Tên đề mục', required=True)
  code = fields.Char(
    string='Mã đề mục',
    help='Mã kỹ thuật, không dấu, viết liền (vd: teacher, student). '
         'Snippet "Course Card" trên website lọc khóa học theo mã này - đổi Tên đề mục '
         'thoải mái không ảnh hưởng, nhưng đổi Mã sẽ khiến snippet tương ứng ngừng lọc '
         'đúng đề mục cho tới khi cập nhật lại snippet.',
  )
  sequence = fields.Integer(default=10)
  color = fields.Integer(string='Màu')

  _sql_constraints = [
    ('code_unique', 'unique(code)', 'Mã đề mục phải là duy nhất!'),
  ]

# ---
# Khóa học
# ---

class SerotoCourse(models.Model):
  _name = 'seroto.course'
  _description = 'Khóa học'
  _inherit = [
    'mail.thread',
    'mail.activity.mixin'
  ]
  _order= 'name asc'

  name = fields.Char(
    string='Tên khóa học',
    required=True,
    tracking=True
  )

  code = fields.Char(
    string='Mã khóa học',
    required=True,
    copy=False
  )

  category_id = fields.Many2one(
    'product.category',
    string='Danh mục'
  )

  active = fields.Boolean(default=True)

  state = fields.Selection(
      selection=[
      ('draft',     'Đang chờ'),
      ('published', 'Đang mở đăng ký'),
      ('closed',    'Đóng đăng ký'),
      ('archived',  'Lưu trữ'),
    ],
    string='Trạng thái',
    default='draft',
    tracking=True,
  )

  tuition_fee = fields.Monetary(
    string='Học phí niêm yết',
    currency_field='currency_id',
    tracking=True,
  )

  currency_id = fields.Many2one(
    'res.currency',
    default=lambda self: self.env.company.currency_id,
  )

  tax_ids = fields.Many2many(
    comodel_name='account.tax',
    string='Thuế bán hàng',
    domain=[('type_tax_use', '=', 'sale')],
    help='Thuế sẽ áp dụng khi tạo Sales Order / Invoice',
  )

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

  objectives = fields.Text(string='Mục tiêu khoá học / Đầu ra')

  subtitle = fields.Char(string='Phụ đề')

  description = fields.Html(string='Mô tả khoá học')

  course_type = fields.Selection([
    ('online', 'Online Zoom'),
    ('offline', 'Offline')
  ],
    string='Hình thức học',
    default='online',
  )

  teacher_id = fields.Many2one(
    'res.partner',
    string='Giảng viên'
  )

  audience_ids = fields.Many2many(
    'seroto.course.audience',
    string='Đối tượng',
    help='Đề mục hiển thị trên website (vd Giáo viên, Học viên). '
         'Một khóa học có thể thuộc nhiều đối tượng cùng lúc.',
  )

  image = fields.Image(related='product_id.image_1920', string='Ảnh khoá học', readonly=False, store=True)

  # --- Lớp học
  class_ids = fields.One2many('seroto.course.class', 'course_id', string='Danh sách lớp')
  class_count = fields.Integer(compute='_compute_class_count', string='Số lớp')

  next_class_id = fields.Many2one(
    'seroto.course.class',
    string='Lớp học gần nhất',
    compute='_compute_next_class',
    help='Lớp chưa/đang học có ngày khai giảng gần nhất kể từ hôm nay. '
         'Dùng để hiển thị "Ngày học" trên website (vd snippet Course Card).',
  )

  # --- Compute
  @api.depends('class_ids')
  def _compute_class_count(self):
      for rec in self:
          rec.class_count = len(rec.class_ids)

  @api.depends('class_ids.date_start', 'class_ids.state')
  def _compute_next_class(self):
    today = fields.Date.context_today(self)
    for rec in self:
      # Ưu tiên lớp đang "Đang học" (đã khai giảng, có thể trước hôm nay) - lấy lớp có
      # ngày khai giảng gần đây nhất nếu có nhiều lớp đang học cùng lúc.
      ongoing = rec.class_ids.filtered(lambda c: c.state == 'ongoing').sorted('date_start', reverse=True)
      if ongoing:
        rec.next_class_id = ongoing[:1]
        continue
      # Không có lớp đang học thì lấy lớp "Chờ khai giảng" gần nhất trong tương lai.
      upcoming = rec.class_ids.filtered(
        lambda c: c.state == 'scheduled' and c.date_start and c.date_start >= today
      ).sorted('date_start')
      rec.next_class_id = upcoming[:1]

  @api.depends('product_id')
  def _compute_product_variant(self):
    for rec in self:
      if rec.product_id:
        rec.product_variant_id = rec.product_id.product_variant_id
      else:
        rec.product_variant_id = False

  # --- Tạo / Đồng bộ product.template
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
      'res_model': 'seroto.course.class',
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

  def action_reopen(self):
    self.write({'state': 'draft'})

  _sql_constraints = [
    ('code_unique', 'unique(code)', 'Mã khoá học phải là duy nhất!'),
  ]

# ---
# Lớp học
# ---

class SerotoCourseClass(models.Model):
  _name = 'seroto.course.class'
  _description = 'Lớp học'
  _inherit = ['mail.thread', 'mail.activity.mixin']
  _order = 'date_start desc, name asc'

  name = fields.Char(string='Tên lớp', required=True, tracking=True)
  code = fields.Char(string='Mã lớp', required=True, copy=False)
  course_id = fields.Many2one(
    'seroto.course',
    string='Khóa học',
    required=True,
    ondelete='restrict',
    tracking=True
  )
  teacher_id = fields.Many2one('res.partner', string='Giáo viên / Giảng viên', tracking=True)
  course_type = fields.Selection(
    related='course_id.course_type',
    string='Hình thức học',
    store=True,
    readonly=False,
  )
  state = fields.Selection([
    ('scheduled', 'Chờ khai giảng'),
    ('ongoing', 'Đang học'),
    ('completed', 'Đã kết thúc'),
    ('cancelled', 'Hủy'),
  ],
    string='Trạng thái lớp',
    default='scheduled',
    tracking=True
  )

  date_start = fields.Date(string='Ngày khai giảng', tracking=True)
  date_end = fields.Date(string='Ngày kết thúc dự kiến', tracking=True)
  schedule_note = fields.Text(string='Lịch học', help='VD: Thứ 2-4-6, 18:00–20:00')
  registration_deadline = fields.Date(
    string='Thời hạn đăng ký'
  )

  max_students = fields.Integer(string='Sĩ số tối đa', default=20)
  enrollment_ids = fields.One2many('seroto.enrollment', 'class_id', string='Danh sách học viên')
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

  note = fields.Text(string='Ghi chú')

  session_ids = fields.One2many('seroto.course.session', 'class_id', string='Danh sách buổi học')
  session_count = fields.Integer(compute='_compute_session_count', string='Số buổi')

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

  def action_view_students(self):
    self.ensure_one()
    students = self.enrollment_ids.mapped('student_id')
    return {
      'type': 'ir.actions.act_window',
      'name': f'Danh sách học viên {self.name}',
      'res_model': 'seroto.student',
      'view_mode': 'list,form',
      'domain': [('id', 'in', students.ids)],
    }

  def action_view_sessions(self):
    self.ensure_one()
    return {
      'type': 'ir.actions.act_window',
      'name': f'Buổi học của {self.name}',
      'res_model': 'seroto.course.session',
      'view_mode': 'list,form',
      'domain': [('class_id', '=', self.id)],
      'context': {'default_class_id': self.id},
    }

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

# ---
# Buổi học
# ---

class SerotoCourseSession(models.Model):
  _name = 'seroto.course.session'
  _description = 'Buổi học'
  _order = 'sequence asc'

  name = fields.Char(string='Tên buổi học', required=True)
  sequence = fields.Integer(string='Thứ tự buổi', default=1)
  class_id = fields.Many2one('seroto.course.class', string='Lớp học', required=True, ondelete='cascade')
  teacher_id = fields.Many2one(
    'res.partner',
    string='Giáo viên',
    related='class_id.teacher_id',
    store=True
  )

  date_session = fields.Date(string='Ngày học', required=True)
  time_start = fields.Float(string='Giờ bắt đầu', help='VD: 18.0 = 18:00')
  time_end = fields.Float(string='Giờ kết thúc')
  duration = fields.Float(string='Thời lượng (giờ)', compute='_compute_duration', store=True)

  topic = fields.Char(string='Chủ đề / Nội dung buổi học')
  description = fields.Text(string='Mô tả chi tiết')

  state = fields.Selection(
    [
      ('planned',   'Chờ học'),
      ('ongoing', 'Đang học'),
      ('completed', 'Hoàn thành'),
      ('cancelled', 'Huỷ / Nghỉ'),
      ('postponed', 'Dời lịch'),
    ],
    string='Trạng thái',
    default='planned',
  )

  def action_start_session(self):
    self.write({'state': 'ongoing'})

  def action_complete_session(self):
    self.write({'state': 'completed'})

  @api.depends('time_start', 'time_end')
  def _compute_duration(self):
    for rec in self:
      rec.duration = max(0.0, rec.time_end - rec.time_start)