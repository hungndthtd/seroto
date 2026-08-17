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
    # Cờ RIÊNG cho việc hiển thị công khai trên website - tách biệt với "active" (cơ chế
    # lưu trữ/ẩn chung của Odoo). Mặc định False: khóa học mới tạo (có thể chưa điền
    # xong thông tin) sẽ KHÔNG tự xuất hiện trên bất kỳ snippet nào cho tới khi staff
    # chủ động bật - xem controllers/academic_course_snippet.py (module
    # vtt_seroto_website), route lọc field này BẮT BUỘC dù có/không có Mã đối tượng.
    is_published = fields.Boolean(string='Hiển thị trên Website', default=False)
    slogan = fields.Char(string='Slogan/Mô tả ngắn')
    description = fields.Text(string='Mô tả chi tiết')
    format = fields.Char(string='Hình thức học', default='Online Zoom')
    lecturer = fields.Char(string='Giảng viên/Cố vấn')
    # Có điền thì website hiện thêm nút "Chi tiết" cạnh "Đăng ký ngay" (mở tab mới) -
    # xem controllers/academic_course_snippet.py (module vtt_seroto_website) +
    # static/src/js/course_group_snippet.js, để trống thì chỉ hiện "Đăng ký ngay".
    detail_url = fields.Char(string='Link chi tiết', help='VD: /khoa-hoc-eq-5-phut hoặc URL đầy đủ.')

    batch_info = fields.Char(string='Đợt tuyển sinh', placeholder='Đang mở đăng ký K48')
    schedule_date = fields.Char(string='Ngày học', placeholder='06/07 - 26/07')
    schedule_time = fields.Char(string='Giờ học/Thời gian', placeholder='5:00 - 6:00')
    deadline_register = fields.Char(string='Thời hạn đăng ký', placeholder='17h 29/06')

    registration_open_date = fields.Date(string='Ngày mở đăng ký')
    registration_close_date = fields.Date(string='Ngày đóng đăng ký')

    default_class_id = fields.Many2one(
        'academic.class', string='Lớp nhận đăng ký',
        domain="[('course_id', '=', id), ('state', 'in', ['draft', 'open'])]",
        help='Lớp học mà hệ thống sẽ tự động gắn vào phiếu đăng ký khi khách đăng ký khóa học này từ website.',
    )
    intake_ids = fields.One2many('academic.intake', 'course_id', string='Các đợt học')
    class_ids = fields.One2many('academic.class', 'course_id', string='Các lớp học')

    is_registration_open = fields.Boolean(string='Đang mở đăng ký', compute='_compute_is_registration_open')

    @api.depends('registration_open_date', 'registration_close_date')
    def _compute_is_registration_open(self):
        today = fields.Date.context_today(self)
        for course in self:
            open_ok = not course.registration_open_date or course.registration_open_date <= today
            close_ok = not course.registration_close_date or course.registration_close_date >= today
            course.is_registration_open = open_ok and close_ok

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

    # Đề mục (Giáo viên/Trường học/...) - website (vtt_seroto_website, snippet "Khóa
    # học - Nhóm đối tượng") lọc khóa học hiển thị theo audience_ids.code, khớp với mã
    # nhập ở panel Tùy chỉnh của snippet đó.
    audience_ids = fields.Many2many(
        'academic.course.audience', string='Đối tượng',
        help='Đề mục hiển thị trên website (vd Giáo viên, Trường học). Một khóa học '
             'có thể thuộc nhiều đối tượng cùng lúc.',
    )

    def action_open_new_batch(self):
        self.ensure_one()
        return {
            'name': 'Mở đợt học mới',
            'type': 'ir.actions.act_window',
            'res_model': 'academic.batch.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_course_id': self.id},
        }


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    course_id = fields.Many2one('academic.course', string='Khóa học liên kết',
        compute='_compute_course_id', readonly=False)

    def _compute_course_id(self):
        for prod in self:
            course = self.env['academic.course'].search([('product_id', '=', prod.id)], limit=1)
            prod.course_id = course.id if course else False
