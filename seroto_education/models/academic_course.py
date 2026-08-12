# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AcademicCourse(models.Model):
    _name = 'academic.course'
    _description = 'Khóa học'
    _inherit = ['image.mixin']

    code = fields.Char(string='Mã khóa học', required=True, default='KH')

    def init(self):
        super(AcademicCourse, self).init()
        self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='academic_course' AND column_name='code'")
        if not self.env.cr.fetchone():
            self.env.cr.execute("ALTER TABLE academic_course ADD COLUMN code VARCHAR")
            self.env.cr.commit()
    name = fields.Char(string='Tên khóa học', required=True)
    active = fields.Boolean(string='Kích hoạt', default=True)
    slogan = fields.Char(string='Slogan/Mô tả ngắn')
    description = fields.Text(string='Mô tả chi tiết')
    format = fields.Char(string='Hình thức học', default='Online Zoom')
    lecturer = fields.Char(string='Giảng viên/Cố vấn')
    
    batch_info = fields.Char(string='Đợt tuyển sinh', placeholder='Đang mở đăng ký K48')
    schedule_date = fields.Char(string='Ngày học', placeholder='06/07 - 26/07')
    schedule_time = fields.Char(string='Giờ học/Thời gian', placeholder='5:00 - 6:00')
    deadline_register = fields.Char(string='Thời hạn đăng ký', placeholder='17h 29/06')

    @api.depends('code', 'name')
    def _compute_display_name(self):
        self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='academic_course' AND column_name='code'")
        has_code = self.env.cr.fetchone()
        for course in self:
            if has_code and course.code:
                course.display_name = f"[{course.code}] {course.name}"
            else:
                course.display_name = course.name

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=100, order=None):
        domain = domain or []
        if name:
            self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='academic_course' AND column_name='code'")
            if self.env.cr.fetchone():
                domain = ['|', ('code', operator, name), ('name', operator, name)] + domain
            else:
                domain = [('name', operator, name)] + domain
        return super(AcademicCourse, self)._name_search(name, domain=domain, operator=operator, limit=limit, order=order)

    product_id = fields.Many2one('product.template', string='Sản phẩm liên kết',
        domain=[('type', '=', 'service')], required=True)

    # Mỗi khóa học 1 bộ câu hỏi riêng - website (vtt_seroto_website, wizard đăng ký
    # nhiều bước) đọc lại đúng bộ câu hỏi của khóa học đang đăng ký ở bước "Thông tin
    # chuyên sâu" để khách điền câu trả lời.
    question_ids = fields.One2many(
        'academic.course.question', 'course_id', string='Câu hỏi chuyên sâu',
    )


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    course_id = fields.Many2one('academic.course', string='Khóa học liên kết',
        compute='_compute_course_id', readonly=False)

    def _compute_course_id(self):
        for prod in self:
            course = self.env['academic.course'].search([('product_id', '=', prod.id)], limit=1)
            prod.course_id = course.id if course else False
