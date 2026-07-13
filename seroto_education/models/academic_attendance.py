# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AcademicAttendance(models.Model):
    _name = 'academic.attendance'
    _description = 'Điểm danh'
    _rec_name = 'session_id'

    session_id = fields.Many2one('academic.session', string='Buổi học', required=True, ondelete='cascade')
    class_id = fields.Many2one('academic.class', string='Lớp học', related='session_id.class_id', store=True, readonly=True)
    course_id = fields.Many2one('academic.course', string='Khóa học', related='session_id.class_id.course_id', store=True, readonly=True)
    date_start = fields.Datetime(string='Thời gian học', related='session_id.date_start', store=True, readonly=True)
    student_id = fields.Many2one('res.partner', string='Học viên', required=True)
    
    state = fields.Selection([
        ('present', 'Có mặt'),
        ('absent_perm', 'Vắng có phép'),
        ('absent_noperm', 'Vắng không phép'),
        ('late', 'Muộn')
    ], string='Trạng thái điểm danh', default='present', required=True)

    _session_student_unique = models.Constraint(
        'unique(session_id, student_id)',
        'Mỗi học viên chỉ được điểm danh một lần trong một buổi học!'
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super(AcademicAttendance, self).create(vals_list)
        for record in records:
            # Check for consecutive absences
            if record.state == 'absent_noperm':
                record._check_consecutive_absences()
            # Trigger progress recalculation
            record._recompute_enrollment_progress()
        return records

    def write(self, vals):
        res = super(AcademicAttendance, self).write(vals)
        if 'state' in vals:
            for record in self:
                if record.state == 'absent_noperm':
                    record._check_consecutive_absences()
                record._recompute_enrollment_progress()
        return res

    def _recompute_enrollment_progress(self):
        for record in self:
            enrollments = self.env['academic.enrollment'].search([
                ('student_id', '=', record.student_id.id),
                ('class_id', '=', record.session_id.class_id.id)
            ])
            if enrollments:
                enrollments._compute_progress()

    def _check_consecutive_absences(self):
        self.ensure_one()
        # Find all sessions of this class sorted by start date
        sessions = self.env['academic.session'].search([
            ('class_id', '=', self.session_id.class_id.id)
        ], order='date_start desc')
        
        if len(sessions) < 2:
            return
            
        # Check the last two attendances
        last_attendances = self.env['academic.attendance'].search([
            ('session_id', 'in', sessions.ids),
            ('student_id', '=', self.student_id.id)
        ], order='id desc', limit=2)
        
        if len(last_attendances) == 2:
            if all(att.state == 'absent_noperm' for att in last_attendances):
                # Create a task or activity for student care
                # Find if there is an active CRM lead or just log an activity on the Contact (res.partner)
                partner = self.student_id
                activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
                if activity_type:
                    self.env['mail.activity'].create({
                        'activity_type_id': activity_type.id,
                        'note': f"Học viên {partner.name} đã vắng không phép 2 buổi liên tiếp ở lớp {self.session_id.class_id.name}. Cần liên hệ chăm sóc gấp!",
                        'summary': 'Cảnh báo vắng học liên tiếp',
                        'res_id': partner.id,
                        'res_model_id': self.env['ir.model']._get('res.partner').id,
                        'user_id': self.env.user.id,
                    })

    def action_set_present(self):
        for rec in self:
            rec.state = 'present'

    def action_set_late(self):
        for rec in self:
            rec.state = 'late'

    def action_set_absent_noperm(self):
        for rec in self:
            rec.state = 'absent_noperm'

    def action_set_absent_perm(self):
        for rec in self:
            rec.state = 'absent_perm'

