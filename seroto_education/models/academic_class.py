from odoo import models, fields, api

class AcademicClass(models.Model):
    _name = 'academic.class'
    _description = 'Lớp học'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Tên lớp học', required=True, tracking=True)
    course_id = fields.Many2one('academic.course', string='Khóa học', required=True, tracking=True)
    intake_id = fields.Many2one('academic.intake', string='Đợt học', required=True, tracking=True)
    teacher_ids = fields.Many2many('res.partner', string='Giảng viên', domain=[('is_teacher', '=', True)], tracking=True)
    active = fields.Boolean(string='Kích hoạt', default=True, tracking=True)
    
    session_ids = fields.One2many('academic.session', 'class_id', string='Các buổi học')
    enrollment_ids = fields.One2many('academic.enrollment', 'class_id', string='Học viên ghi danh')
    
    attendance_count = fields.Integer(string='Số lượt điểm danh', compute='_compute_attendance_count')
    date_start = fields.Date(string='Ngày bắt đầu', compute='_compute_dates', store=True)
    date_end = fields.Date(string='Ngày kết thúc', compute='_compute_dates', store=True)

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
