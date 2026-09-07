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
    # vtt_seroto_website), route lọc field này BẮT BUỘC dù có/không có Mã khu vực hiển thị.
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

    default_class_id = fields.Many2one(
        'academic.class', string='Lớp nhận đăng ký',
        domain="[('course_id', '=', id), ('state', 'in', ['draft', 'open'])]",
        help='Lớp học mà hệ thống sẽ tự động gắn vào phiếu đăng ký khi khách đăng ký khóa học này từ website.',
    )
    intake_ids = fields.One2many('academic.intake', 'course_id', string='Các đợt học')
    class_ids = fields.One2many('academic.class', 'course_id', string='Các lớp học')

    # Trước đây tính theo 2 field ngày riêng (registration_open_date/close_date) hoàn
    # toàn TÁCH BIỆT với trạng thái Lớp học - gây lỗi thật: Quản lý bấm "Đóng đăng ký"
    # trên Lớp học nhưng website vẫn nhận đăng ký bình thường vì không liên quan gì tới
    # nhau. Bỏ hẳn 2 field ngày đó, chỉ còn ĐÚNG 1 nguồn sự thật: website chỉ nhận đăng
    # ký khi "Lớp nhận đăng ký" (default_class_id) đang ở trạng thái "Đang nhận đăng ký"
    # - Quản lý chỉ cần thao tác đúng 1 chỗ quen thuộc (nút Mở/Đóng đăng ký trên Lớp học).
    is_registration_open = fields.Boolean(
        string='Đang mở đăng ký', compute='_compute_is_registration_open', store=True,
        help='Website chỉ cho đăng ký khóa học này khi "Lớp nhận đăng ký" đang ở trạng thái "Đang nhận đăng ký".',
    )

    @api.depends('default_class_id.state')
    def _compute_is_registration_open(self):
        for course in self:
            course.is_registration_open = bool(course.default_class_id) and course.default_class_id.state == 'open'

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

    # related + readonly=False - field "ảo" ĐỌC/GHI THẲNG vào product_id.list_price,
    # cùng kỹ thuật với ProductTemplate.course_id bên dưới (compute + readonly=False).
    # Sửa giá ở đây trên form Khóa học sẽ đổi LUÔN giá bán thật của Sản phẩm liên kết -
    # không có bản sao/field riêng nào khác, tuyệt đối không lệch nhau. PHẢI khai Float
    # (không phải Monetary) - product.template.list_price tự nó là Float, related field
    # bắt buộc khớp kiểu với field nguồn (hiển thị dạng tiền qua widget="monetary" ở
    # view, đúng cách core product hiển thị field này).
    course_price = fields.Float(
        string='Học phí tương ứng', related='product_id.list_price', readonly=False,
        help='Sửa trực tiếp tại đây sẽ đổi luôn giá bán của Sản phẩm liên kết.',
    )

    # currency_id CHỈ để early_price (academic.course.pricing) hiện đúng đơn vị tiền tệ
    # (VNĐ) - không có ý nghĩa đa tiền tệ gì khác, luôn là tiền tệ của công ty (cùng quy
    # ước với currency_id của seroto.course.registration bên vtt_seroto_website).
    currency_id = fields.Many2one(
        'res.currency', string='Đơn vị tiền tệ', default=lambda self: self.env.company.currency_id,
    )
    # Cấu hình giá theo "Diện đăng ký" (seroto.course.registration.registration_category,
    # module vtt_seroto_website) NGAY TRÊN Khóa học - nhân viên tạo Phiếu đăng ký không
    # phải tự tính tay, vẫn sửa được riêng cho từng phiếu nếu cần (xem
    # seroto.course.registration.early_price/discount_percent). 5 dòng CỐ ĐỊNH (1 diện/
    # dòng, xem create() bên dưới) - hiển thị dạng list bên tab "Cấu hình giá theo diện
    # đăng ký" (academic_course_views.xml), cột "Ưu đãi" chỉ để xem, sửa số/liên kết
    # thật phải bấm vào dòng để mở form riêng (xem academic.course.pricing).
    pricing_ids = fields.One2many(
        'academic.course.pricing', 'course_id', string='Cấu hình giá theo diện đăng ký',
    )

    @api.model_create_multi
    def create(self, vals_list):
        courses = super().create(vals_list)
        Pricing = self.env['academic.course.pricing']
        categories = [c for c, _label in Pricing._fields['registration_category'].selection]
        for course in courses:
            if course.pricing_ids:
                continue
            Pricing.create([
                {'course_id': course.id, 'registration_category': category}
                for category in categories
            ])
        return courses

    # Mỗi khóa học 1 bộ câu hỏi riêng - website (vtt_seroto_website, wizard đăng ký
    # nhiều bước) đọc lại đúng bộ câu hỏi của khóa học đang đăng ký ở bước "Thông tin
    # chuyên sâu" để khách điền câu trả lời.
    question_ids = fields.One2many(
        'academic.course.question', 'course_id', string='Câu hỏi chuyên sâu',
    )

    # Khu vực hiển thị (trang chủ theo Giáo viên/Trường học/...) - website
    # (vtt_seroto_website, snippet "Khóa học - Khu vực hiển thị") lọc khóa học hiển thị
    # theo audience_ids.code, khớp với mã nhập ở panel Tùy chỉnh của snippet đó. Field/
    # model kỹ thuật vẫn giữ tên cũ (audience_ids, academic.course.audience) để không
    # phải đổi cấu trúc bảng/mất dữ liệu cũ - chỉ đổi nhãn hiển thị cho người dùng.
    audience_ids = fields.Many2many(
        'academic.course.audience', string='Khu vực hiển thị',
        help='Khu vực hiển thị trên website (vd trang chủ theo Giáo viên, Trường học...). '
             'Một khóa học có thể xuất hiện ở nhiều khu vực cùng lúc.',
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
