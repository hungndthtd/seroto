# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    enrollment_ids = fields.One2many('academic.enrollment', 'student_id', string='Lịch sử ghi danh')
    is_student = fields.Boolean(string='Là học viên', compute='_compute_is_student', store=True, index=True)
    student_code = fields.Char(string='Mã học viên', readonly=True, copy=False, index=True)
    birthdate = fields.Date(string='Ngày sinh')
    occupation = fields.Char(string='Nghề nghiệp')
    is_teacher = fields.Boolean(string='Là giảng viên', default=False)
    taught_class_ids = fields.Many2many('academic.class', string='Lớp giảng dạy', compute='_compute_taught_class_ids')

    def _compute_taught_class_ids(self):
        for partner in self:
            partner.taught_class_ids = self.env['academic.class'].search([('teacher_ids', '=', partner.id)])

    def init(self):
        super(ResPartner, self).init()
        # Check student_code
        self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='res_partner' AND column_name='student_code'")
        if not self.env.cr.fetchone():
            self.env.cr.execute("ALTER TABLE res_partner ADD COLUMN student_code VARCHAR")
            self.env.cr.commit()
        # Check birthdate
        self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='res_partner' AND column_name='birthdate'")
        if not self.env.cr.fetchone():
            self.env.cr.execute("ALTER TABLE res_partner ADD COLUMN birthdate DATE")
            self.env.cr.commit()
        # Check occupation
        self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='res_partner' AND column_name='occupation'")
        if not self.env.cr.fetchone():
            self.env.cr.execute("ALTER TABLE res_partner ADD COLUMN occupation VARCHAR")
            self.env.cr.commit()
        # Check is_teacher
        self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='res_partner' AND column_name='is_teacher'")
        if not self.env.cr.fetchone():
            self.env.cr.execute("ALTER TABLE res_partner ADD COLUMN is_teacher BOOLEAN DEFAULT FALSE")
            self.env.cr.commit()

    @api.depends('enrollment_ids', 'enrollment_ids.state')
    def _compute_is_student(self):
        for partner in self:
            is_std = any(e.state != 'cancel' for e in partner.enrollment_ids)
            partner.is_student = is_std
            if is_std and not partner.student_code:
                partner.student_code = self.env['ir.sequence'].next_by_code('academic.student')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_student') and not vals.get('student_code'):
                vals['student_code'] = self.env['ir.sequence'].next_by_code('academic.student')
        return super(ResPartner, self).create(vals_list)

    def write(self, vals):
        res = super(ResPartner, self).write(vals)
        if vals.get('is_student'):
            for partner in self:
                if not partner.student_code:
                    partner.student_code = self.env['ir.sequence'].next_by_code('academic.student')
        return res

    @api.depends('student_code')
    def _compute_display_name(self):
        super()._compute_display_name()
        # Safeguard: only access student_code if the column has been created in the database
        self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='res_partner' AND column_name='student_code'")
        if not self.env.cr.fetchone():
            return
        for partner in self:
            if partner.is_student and partner.student_code:
                partner.display_name = f"[{partner.student_code}] {partner.name}"

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=100, order=None):
        domain = domain or []
        if name:
            self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='res_partner' AND column_name='student_code'")
            if self.env.cr.fetchone():
                domain = ['|', ('student_code', operator, name), ('name', operator, name)] + domain
            else:
                domain = [('name', operator, name)] + domain
        return super(ResPartner, self)._name_search(name, domain=domain, operator=operator, limit=limit, order=order)
