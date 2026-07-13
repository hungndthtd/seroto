# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AcademicEnrollment(models.Model):
    _name = 'academic.enrollment'
    _description = 'Ghi danh'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_enroll desc, id desc'
    _rec_name = 'student_id'

    student_id = fields.Many2one('res.partner', string='Học viên', domain=[('is_company', '=', False)], required=True, tracking=True)
    class_id = fields.Many2one('academic.class', string='Lớp học', required=True, tracking=True)
    course_id = fields.Many2one('academic.course', string='Khóa học', related='class_id.course_id', store=True)
    sale_order_id = fields.Many2one('sale.order', string='Đơn hàng gốc')
    date_enroll = fields.Date(string='Ngày ghi danh', default=fields.Date.context_today, required=True, index=True, tracking=True)
    
    state = fields.Selection([
        ('draft', 'Chờ thanh toán'),
        ('enrolled', 'Đã ghi danh'),
        ('suspended', 'Bảo lưu'),
        ('completed', 'Hoàn thành'),
        ('cancel', 'Đã hủy')
    ], string='Trạng thái', default='draft', required=True, tracking=True)

    progress = fields.Float(string='Tiến độ học (%)', compute='_compute_progress', store=True)
    score = fields.Float(string='Điểm số')
    note = fields.Text(string='Ghi chú kết quả')
    sessions_attended = fields.Integer(string='Số buổi đã học', compute='_compute_progress', store=True)
    sessions_total = fields.Integer(string='Tổng số buổi học', compute='_compute_progress', store=True)
    sessions_summary = fields.Char(string='Tóm tắt buổi học', compute='_compute_progress', store=True)

    def init(self):
        super(AcademicEnrollment, self).init()
        # SQL Migration: Update old in_progress state to enrolled
        self.env.cr.execute("UPDATE academic_enrollment SET state='enrolled' WHERE state='in_progress'")
        self.env.cr.commit()
        # Check sessions_attended
        self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='academic_enrollment' AND column_name='sessions_attended'")
        if not self.env.cr.fetchone():
            self.env.cr.execute("ALTER TABLE academic_enrollment ADD COLUMN sessions_attended INTEGER")
            self.env.cr.commit()
        # Check sessions_total
        self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='academic_enrollment' AND column_name='sessions_total'")
        if not self.env.cr.fetchone():
            self.env.cr.execute("ALTER TABLE academic_enrollment ADD COLUMN sessions_total INTEGER")
            self.env.cr.commit()
        # Check sessions_summary
        self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='academic_enrollment' AND column_name='sessions_summary'")
        if not self.env.cr.fetchone():
            self.env.cr.execute("ALTER TABLE academic_enrollment ADD COLUMN sessions_summary VARCHAR")
            self.env.cr.commit()
        # Check date_enroll
        self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='academic_enrollment' AND column_name='date_enroll'")
        if not self.env.cr.fetchone():
            self.env.cr.execute("ALTER TABLE academic_enrollment ADD COLUMN date_enroll DATE")
            self.env.cr.commit()

    @api.depends('class_id', 'student_id')
    def _compute_progress(self):
        for rec in self:
            if not rec.class_id or not rec.student_id:
                rec.progress = 0.0
                rec.sessions_attended = 0
                rec.sessions_total = 0
                rec.sessions_summary = "0 / 0"
                continue
                
            total_held = self.env['academic.session'].search_count([
                ('class_id', '=', rec.class_id.id),
                ('date_start', '<=', fields.Datetime.now())
            ])
            if not total_held:
                rec.progress = 0.0
                rec.sessions_attended = 0
                rec.sessions_total = 0
                rec.sessions_summary = "0 / 0"
                continue
                
            attendances = self.env['academic.attendance'].search([
                ('student_id', '=', rec.student_id.id),
                ('session_id.class_id', '=', rec.class_id.id),
                ('session_id.date_start', '<=', fields.Datetime.now())
            ])
            present_or_late = len(attendances.filtered(lambda a: a.state in ('present', 'late')))
            
            # Write directly to bypass compute cache triggers in write method if called
            rec.sessions_attended = present_or_late
            rec.sessions_total = total_held
            rec.sessions_summary = f"{present_or_late}/{total_held}"
            
            # Safeguard progress calculation
            if total_held <= 0:
                rec.progress = 0.0
                continue
                
            rec.progress = (present_or_late / total_held) * 100.0
            
    def action_complete(self):
        for rec in self:
            rec.state = 'completed'
            # Trigger certificate generation automatically
            self.env['academic.certificate'].create({
                'student_id': rec.student_id.id,
                'course_id': rec.course_id.id,
                'class_id': rec.class_id.id,
                'grade': 'passed' if rec.progress >= 50.0 else 'failed'
            })

    def action_suspend(self):
        for rec in self:
            if rec.state == 'enrolled':
                rec.state = 'suspended'
                rec.message_post(body="Học viên đã được xin bảo lưu khóa học.")

    def action_resume(self):
        for rec in self:
            if rec.state == 'suspended':
                rec.state = 'enrolled'
                rec.message_post(body="Học viên đã khôi phục việc học và tiếp tục khóa học.")
