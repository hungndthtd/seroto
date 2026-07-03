from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

class SerotoStudent(models.Model):
  _name = 'seroto.student'
  _description = 'Học viên'
  _inherit = ['mail.thread', 'mail.activity.mixin']
  _order = 'name asc'

  partner_id = fields.Many2one(
    "res.partner",
    required=True,
    ondelete="restrict",
  )

  name = fields.Char(
    related='partner_id.name',
    string='Họ và tên',
    required=True,
    tracking=True
  )

  student_code = fields.Char(
    string='Mã học viên',
    required=True,
    copy=False,
    readonly=True,
    default=lambda self: _('New'),
    tracking=True
  )

  state = fields.Selection([
    ('new', 'Mới tiếp nhận'),
    ('active', 'Đang học'),
    ('stop', 'Tạm dừng'),
    ('on_leave', 'Bảo lưu'),
    ('completed', 'Hoàn thành'),
  ],
    string='Trạng thái',
    default='new',
    required=True,
    tracking=True
  )

  date_of_birth = fields.Date(string='Ngày sinh', tracking=True)
  age = fields.Integer(string='Tuổi', compute='_compute_age', store=False)
  gender = fields.Selection([
    ('male', 'Nam'),
    ('female', 'Nữ'),
    ('other', 'Khác')
  ],
    string='Giới tính',
    tracking=True
  )

  phone = fields.Char(related='partner_id.phone', string='Số điện thoại', tracking=True, readonly=False, store=True)
  email = fields.Char(related='partner_id.email', string='Email', tracking=True, readonly=False, store=True)

  image = fields.Image(string='Ảnh học viên', max_width=256, max_height=256)

  enrollment_ids = fields.One2many(
    comodel_name='seroto.enrollment',
    inverse_name='student_id',
    string='Danh sách đăng ký học',
  )
  enrollment_count = fields.Integer(
    string='Số khoá đăng ký',
    compute='_compute_enrollment_count',
  )
  active_class_ids = fields.Many2many(
    comodel_name='seroto.course.class',
    string='Lớp đang học',
    compute='_compute_active_classes',
  )

  certificate_type = fields.Selection(
    [
      ('internal', 'Chứng chỉ nội bộ')
    ],
    string='Loại chứng chỉ',
    required=True,
    default='internal',
  )

  date_of_issue = fields.Date(string='Ngày cấp', tracking=True)

  attachment_ids = fields.Many2many(
    comodel_name='ir.attachment',
    string='File đính kèm',
  )

  # --- Compute
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

  # --- Sequence
  @api.model_create_multi
  def create(self, vals_list):
    for vals in vals_list:
      if vals.get('student_code', _('New')) == _('New'):
        vals['student_code'] = self.env['ir.sequence'].next_by_code('seroto.student') or _('New')
    return super().create(vals_list)

  # --- Actions
  def action_view_enrollments(self):
    return {
      'type': 'ir.actions.act_window',
      'name': f'Đăng ký học – {self.name}',
      'res_model': 'seroto.enrollment',
      'view_mode': 'list,form',
      'domain': [('student_id', '=', self.id)],
    }

  def action_set_on_leave(self):
    self.write({'state': 'on_leave'})

  def action_set_active(self):
    self.write({'state': 'active'})

  def action_set_stop(self):
    self.write({'state': 'stop'})

  def action_set_completed(self):
    self.write({'state': 'completed'})

  # ── Constraints ──────────────────────────────────────────────────────────
  _sql_constraints = [
    ('student_code_unique', 'unique(student_code)', 'Mã học viên phải là duy nhất!'),
  ]

  @api.constrains('date_of_birth')
  def _check_date_of_birth(self):
    for rec in self:
      if rec.date_of_birth and rec.date_of_birth > fields.Date.today():
        raise ValidationError(_('Ngày sinh không thể là ngày trong tương lai.'))

# ---
# Đăng ký học
# ---

class SerotoEnrollment(models.Model):
  _name = 'seroto.enrollment'
  _description = 'Đăng ký học'
  # _inherit = ['mail.thread']
  _order = 'name asc'

  name = fields.Char(
    string='Mã đăng ký',
    required=True,
    copy=False,
    readonly=True,
    default=lambda self: _('New')
  )

  student_id = fields.Many2one(
    comodel_name='seroto.student',
    string='Học viên',
    required=True,
    ondelete='cascade',
    tracking=True
  )

  class_id = fields.Many2one(
    comodel_name='seroto.course.class',
    string='Lớp học',
    required=True,
    tracking=True
  )

  course_id = fields.Many2one(
    comodel_name='seroto.course',
    string='Khóa học',
    related='class_id.course_id',
    store=True
  )

  state = fields.Selection([
    ('registered', 'Đã đăng ký'),
    ('studying', 'Đang học'),
    ('on_leave', 'Bảo lưu'),
    ('completed', 'Hoàn thành'),
    ('failed', 'Không đạt'),
    ('cancelled', 'Hủy')
  ],
    string='Trạng thái',
    default='registered',
    tracking=True
  )

  tuition_fee = fields.Monetary(
    string='Học phí',
    currency_field='currency_id',
    # compute='_compute_amount_paid',
    store=True,
    readonly=False
  )

  payment_status = fields.Selection([
    ('unpaid', 'Chưa thanh toán'),
    ('partial', 'Thanh toán một phần'),
    ('paid', 'Đã thanh toán đủ')
  ],
    string='Tình trạng thanh toán',
    store=True
  )

  currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

  @api.depends('class_id.course_id.tuition_fee')
  def _compute_tuition_fee(self):
    for rec in self:
      if not rec.tuition_fee:
        rec.tuition_fee = rec.class_id.course_id.tuition_fee or 0.0

  @api.model_create_multi
  def create(self, vals_list):
    for vals in vals_list:
      if vals.get('name', _('New')) == _('New'):
        vals['name'] = self.env['ir.sequence'].next_by_code('seroto.enrollment') or _('New')
    return super().create(vals_list)
