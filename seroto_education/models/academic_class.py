from odoo import models, fields, api, _

class AcademicClass(models.Model):
    _name = 'academic.class'
    _description = 'Lớp học'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Tên lớp học', required=True, tracking=True)
    intake_id = fields.Many2one('academic.intake', string='Đợt học', required=True, tracking=True)
    course_id = fields.Many2one(
        'academic.course', string='Khóa học', related='intake_id.course_id',
        store=True, readonly=True, tracking=True,
    )
    state = fields.Selection([
        ('draft', 'Sắp mở'),
        ('open', 'Đang nhận đăng ký'),
        ('closed', 'Đã đóng đăng ký'),
        ('in_progress', 'Đang học'),
        ('done', 'Hoàn thành'),
    ], string='Trạng thái', default='draft', required=True, tracking=True)
    teacher_ids = fields.Many2many('res.partner', string='Giảng viên', domain=[('is_teacher', '=', True)], tracking=True)
    organizer_ids = fields.Many2many(
        'res.partner', 'academic_class_organizer_rel', 'class_id', 'partner_id',
        string='Ban tổ chức', tracking=True,
    )
    volunteer_ids = fields.Many2many(
        'res.partner', 'academic_class_volunteer_rel', 'class_id', 'partner_id',
        string='Người phụng sự', tracking=True,
        help='Hỗ trợ vài việc nhỏ cho Ban tổ chức, không phải thành viên chính thức.',
    )
    active = fields.Boolean(string='Kích hoạt', default=True, tracking=True)
    
    session_ids = fields.One2many('academic.session', 'class_id', string='Các buổi học')
    enrollment_ids = fields.One2many('academic.enrollment', 'class_id', string='Học viên ghi danh')
    
    attendance_count = fields.Integer(string='Số lượt điểm danh', compute='_compute_attendance_count')
    date_start = fields.Date(string='Ngày bắt đầu (thực tế)', compute='_compute_dates', store=True,
        help='Tự tính theo buổi học sớm nhất đã tạo trong lớp.')
    date_end = fields.Date(string='Ngày kết thúc (thực tế)', compute='_compute_dates', store=True,
        help='Tự tính theo buổi học muộn nhất đã tạo trong lớp.')

    date_start_planned = fields.Date(related='intake_id.date_start', string='Ngày bắt đầu (dự kiến)', store=True, readonly=True)
    date_end_planned = fields.Date(related='intake_id.date_end', string='Ngày kết thúc (dự kiến)', store=True, readonly=True)

    # Mốc ngày để tự động xác định "Đăng ký sớm" (Diện đóng học phí, module
    # vtt_seroto_website) - đăng ký TRƯỚC ngày này thì tính là sớm, xem
    # SerotoCourseRegistration.create() (models/course_registration.py bên đó). CHỈ để
    # tính giá - KHÔNG dùng để chặn/mở đăng ký (việc đó vẫn ĐÚNG 1 nguồn sự thật là
    # "state" của lớp, xem academic_course.py is_registration_open - tránh lặp lại lỗi
    # cũ đã từng gặp khi có 2 field ngày tách biệt với trạng thái Lớp học).
    registration_open_date = fields.Date(string='Ngày mở đăng ký')

    def init(self):
        super(AcademicClass, self).init()
        # Check date_start
        self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='academic_class' AND column_name='date_start'")
        if not self.env.cr.fetchone():
            self.env.cr.execute("ALTER TABLE academic_class ADD COLUMN date_start DATE")
            self.env.cr.commit()
        # Check date_end
        self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='academic_class' AND column_name='date_end'")
        if not self.env.cr.fetchone():
            self.env.cr.execute("ALTER TABLE academic_class ADD COLUMN date_end DATE")
            self.env.cr.commit()

    @api.depends('session_ids.date_start', 'session_ids.date_end')
    def _compute_dates(self):
        for rec in self:
            session_starts = rec.session_ids.filtered(lambda s: s.date_start).mapped('date_start')
            session_ends = rec.session_ids.filtered(lambda s: s.date_end).mapped('date_end')
            rec.date_start = min(session_starts).date() if session_starts else False
            rec.date_end = max(session_ends).date() if session_ends else False

    @api.depends('session_ids')
    def _compute_attendance_count(self):
        for rec in self:
            sessions = rec.session_ids
            if sessions:
                rec.attendance_count = self.env['academic.attendance'].search_count([('session_id', 'in', sessions.ids)])
            else:
                rec.attendance_count = 0

    def action_open_registration(self):
        """Website chỉ thật sự nhận đăng ký cho khóa học khi lớp được mở đây ĐANG LÀ
        "Lớp nhận đăng ký" (default_class_id) của khóa - nếu chưa phải, mở đăng ký ở
        đây chưa có tác dụng gì trên website, cần nhắc rõ để không ai tưởng nhầm là đã
        xong (xem academic_course.py, is_registration_open).
        """
        self.write({'state': 'open'})
        not_default = self.filtered(lambda c: c.course_id.default_class_id != c)
        if not_default:
            names = ', '.join(not_default.mapped('name'))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Lưu ý'),
                    'message': _(
                        'Lớp vừa mở đăng ký (%s) hiện CHƯA phải là "Lớp nhận đăng ký" của '
                        'khóa học tương ứng - website sẽ CHƯA cho đăng ký khóa này cho tới '
                        'khi bạn đặt lớp này làm "Lớp nhận đăng ký" trên form Khóa học.'
                    ) % names,
                    'type': 'warning',
                    'sticky': True,
                },
            }

    def action_close_registration(self):
        self.write({'state': 'closed'})
        was_default = self.filtered(lambda c: c.course_id.default_class_id == c)
        if was_default:
            names = ', '.join(was_default.mapped('course_id.name'))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Lưu ý'),
                    'message': _(
                        'Lớp vừa đóng đang là "Lớp nhận đăng ký" của khóa: %s - website sẽ '
                        'tạm ngừng nhận đăng ký khóa này cho tới khi bạn chọn 1 lớp khác làm '
                        '"Lớp nhận đăng ký".'
                    ) % names,
                    'type': 'warning',
                    'sticky': True,
                },
            }

    def action_start_class(self):
        self.write({'state': 'in_progress'})

    def action_complete_class(self):
        self.write({'state': 'done'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_view_attendance(self):
        self.ensure_one()
        return {
            'name': 'Lịch sử điểm danh',
            'type': 'ir.actions.act_window',
            'res_model': 'academic.attendance',
            'view_mode': 'list,form',
            'domain': [('class_id', '=', self.id)],
            'context': {
                'search_default_group_by_session': 1,
            }
        }
