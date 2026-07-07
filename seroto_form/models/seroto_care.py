from odoo import models, fields, api, _

# ---
# Chăm sóc học viên - Bước 1: Điểm danh + Tiến độ học / % hoàn thành
#
# Thiết kế: KHÔNG tạo model "seroto.care" riêng - seroto.enrollment (Đăng ký học) đã
# đúng là đơn vị "1 học viên trong 1 lớp", nên các chỉ số theo dõi được thêm trực tiếp
# vào đó qua _inherit (không đổi field cũ, an toàn, không cần migrate dữ liệu cũ).
#
# Model MỚI duy nhất ở bước này: seroto.attendance (điểm danh từng buổi).
#
# Ảnh hưởng cấu trúc hiện tại:
# - seroto.enrollment: thêm field mới (attendance_ids, total_session_count,
#   attended_session_count, progress_percent, progress_label).
# - seroto.course.session: kế thừa action_start_session để tự tạo điểm danh mặc định
#   "Có mặt" cho học viên đang học của lớp khi buổi học bắt đầu - giáo viên chỉ cần
#   sửa lại học viên nghỉ, không phải điểm danh từ đầu mỗi buổi.
# ---


class SerotoAttendance(models.Model):
  _name = 'seroto.attendance'
  _description = 'Điểm danh'
  _order = 'session_id'

  session_id = fields.Many2one(
    'seroto.course.session',
    string='Buổi học',
    required=True,
    ondelete='cascade',
  )
  enrollment_id = fields.Many2one(
    'seroto.enrollment',
    string='Đăng ký học',
    required=True,
    ondelete='cascade',
  )
  student_id = fields.Many2one(related='enrollment_id.student_id', string='Học viên', store=True)
  class_id = fields.Many2one(related='session_id.class_id', string='Lớp học', store=True)
  date_session = fields.Date(related='session_id.date_session', string='Ngày học', store=True)

  state = fields.Selection([
    ('present', 'Có mặt'),
    ('late', 'Đi trễ'),
    ('absent', 'Vắng không phép'),
    ('excused', 'Vắng có phép'),
  ],
    string='Trạng thái điểm danh',
    default='present',
    required=True,
  )
  is_present = fields.Boolean(
    compute='_compute_is_present', store=True, string='Tính là có mặt',
    help='Có mặt/Đi trễ được tính là có tham gia buổi học khi tính Tỷ lệ chuyên cần; '
         'Vắng (có phép hoặc không) thì không.',
  )

  time_in = fields.Float(string='Giờ vào (thực tế)', help='VD: 18.0 = 18:00')
  time_out = fields.Float(string='Giờ ra (thực tế)')
  late_minutes = fields.Integer(
    compute='_compute_late_minutes', store=True, string='Số phút đi trễ',
  )

  note = fields.Char(string='Ghi chú thêm')
  parent_notified = fields.Boolean(string='Đã thông báo phụ huynh')

  recorded_by_id = fields.Many2one(
    'res.users', string='Người điểm danh', default=lambda self: self.env.user, readonly=True,
  )
  recorded_at = fields.Datetime(
    string='Thời điểm ghi nhận', default=fields.Datetime.now, readonly=True,
  )

  _sql_constraints = [
    ('session_enrollment_unique', 'unique(session_id, enrollment_id)',
     'Học viên này đã được điểm danh cho buổi học này!'),
  ]

  @api.depends('state')
  def _compute_is_present(self):
    for rec in self:
      rec.is_present = rec.state in ('present', 'late')

  @api.depends('time_in', 'session_id.time_start')
  def _compute_late_minutes(self):
    for rec in self:
      if rec.time_in and rec.session_id.time_start and rec.time_in > rec.session_id.time_start:
        rec.late_minutes = round((rec.time_in - rec.session_id.time_start) * 60)
      else:
        rec.late_minutes = 0

  def _compute_display_name(self):
    """Model không có field 'name' riêng nên mặc định Odoo hiện chuỗi kỹ thuật
    'seroto.attendance,NewId_0x...' cho bản ghi mới - đổi thành 'Học viên - Buổi học'
    (hoặc 'Điểm danh mới' khi chưa chọn gì) cho dễ nhìn."""
    for rec in self:
      if rec.student_id and rec.session_id:
        rec.display_name = f'{rec.student_id.name} - {rec.session_id.name}'
      else:
        rec.display_name = _('Mới')

class SerotoCourseSessionCare(models.Model):
  _inherit = 'seroto.course.session'

  attendance_ids = fields.One2many('seroto.attendance', 'session_id', string='Điểm danh')

  def action_start_session(self):
    result = super().action_start_session()
    self._generate_attendance()
    return result

  def _generate_attendance(self):
    """Tự tạo điểm danh mặc định 'Có mặt' cho học viên đang học của lớp khi buổi học
    bắt đầu - giáo viên chỉ cần sửa lại học viên vắng (xem tab "Điểm danh" trên form
    Buổi học)."""
    Attendance = self.env['seroto.attendance']
    for session in self:
      enrollments = session.class_id.enrollment_ids.filtered(
        lambda e: e.state not in ('cancelled', 'failed')
      )
      existing = session.attendance_ids.enrollment_id
      missing = enrollments - existing
      Attendance.create([
        {'session_id': session.id, 'enrollment_id': enrollment.id}
        for enrollment in missing
      ])


class SerotoEnrollmentCare(models.Model):
  _inherit = 'seroto.enrollment'

  attendance_ids = fields.One2many('seroto.attendance', 'enrollment_id', string='Điểm danh')

  total_session_count = fields.Integer(
    compute='_compute_learning_progress', store=True, string='Tổng số buổi',
  )
  attended_session_count = fields.Integer(
    compute='_compute_learning_progress', store=True, string='Số buổi đã học',
  )
  progress_percent = fields.Float(
    compute='_compute_learning_progress', store=True, string='Tỷ lệ chuyên cần (%)',
    help='Tỉ lệ số buổi có mặt / tổng số buổi học của lớp.',
  )
  progress_label = fields.Char(
    compute='_compute_learning_progress', store=True, string='Tiến độ học',
  )

  # "Hoàn thành (%)": chỉ số tổng hợp rộng hơn "Tỷ lệ chuyên cần" (sẽ tính thêm từ bài
  # tập ở bước sau) - hiện tại chưa có dữ liệu bài tập nên để giáo viên/nhân viên tự
  # nhập tay, không compute.
  completion_percent = fields.Float(string='Hoàn thành (%)')

  # --- Kết quả học tập (nhập tay - chưa có hệ thống chấm điểm/bài tập gắn vào)
  average_score = fields.Float(string='Điểm trung bình')
  latest_score = fields.Float(string='Điểm gần nhất')

  # --- Cờ chú ý
  needs_special_care = fields.Boolean(string='Cần chú ý / Chăm sóc đặc biệt')

  # --- Nhận xét giáo viên
  teacher_remark = fields.Text(string='Nhận xét giáo viên')

  @api.depends('attendance_ids.is_present', 'class_id.session_ids')
  def _compute_learning_progress(self):
    for rec in self:
      total_sessions = len(rec.class_id.session_ids)
      attended = len(rec.attendance_ids.filtered(lambda a: a.is_present))

      rec.total_session_count = total_sessions
      rec.attended_session_count = attended
      rec.progress_percent = (attended / total_sessions * 100) if total_sessions else 0.0
      rec.progress_label = _(
        '%(attended)s/%(total)s buổi (%(percent)s%%)',
        attended=attended,
        total=total_sessions,
        percent=int(rec.progress_percent),
      )

  def _compute_display_name(self):
    """Hiện 'Học viên - Lớp học' thay vì mã đăng ký (REG-xxx) - dễ nhìn hơn ở những nơi
    chọn Đăng ký học qua many2one (vd field 'Học viên' trong form Điểm danh)."""
    for rec in self:
      if rec.student_id and rec.class_id:
        rec.display_name = f'{rec.student_id.name} - {rec.class_id.name}'
      else:
        rec.display_name = rec.name
