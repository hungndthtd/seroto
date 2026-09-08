# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SerotoRegistrationCategory(models.Model):
    """Tầng 1 - LOẠI diện đăng ký (đóng học phí/voucher/học bổng...). Mang tính CẤU
    TRÚC, gần như không đổi - chỉ quyết định field/thủ tục riêng nào hiện ra trên Phiếu
    đăng ký và loại này có bắt buộc nhân viên duyệt hồ sơ hay không. KHÔNG chứa % giảm/
    mô tả/mẫu hồ sơ - các thứ đó khác nhau theo TỪNG khóa học, xem
    academic.course.registration.category (Tầng 2) bên dưới.
    """
    _name = 'seroto.registration.category'
    _description = 'Loại diện đăng ký khóa học'
    _order = 'sequence, id'

    name = fields.Char(string='Tên loại diện', required=True)
    code = fields.Selection(
        [
            ('hoc_phi', 'Đóng học phí'),
            ('voucher', 'Voucher quà tặng'),
            ('hb_y_te', 'Học bổng ngành y'),
            ('hb_giao_duc', 'Học bổng giáo dục'),
            ('to_chuc_pldn', 'Tổ chức phi lợi nhuận'),
        ],
        string='Mã kỹ thuật', required=True,
        help='Cố định - quyết định các field riêng nào hiện ra trên Phiếu đăng ký ứng '
             'với loại diện này. Không tạo loại mới với mã chưa có field tương ứng trong code.',
    )
    requires_review = fields.Boolean(
        string='Cần nhân viên duyệt hồ sơ trước khi thanh toán',
        help='Khách nộp hồ sơ xong sẽ ở trạng thái "Chờ duyệt hồ sơ" - Sale/Quản lý xem '
             'chứng từ, Duyệt thì mới tạo link thanh toán (hoặc ghi danh thẳng nếu miễn '
             '100% học phí). Không tick: đi thẳng luồng thanh toán tự động như trước.',
    )
    requires_upload = fields.Boolean(string='Yêu cầu tải lên chứng từ')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Mỗi mã kỹ thuật chỉ được dùng cho đúng 1 loại diện đăng ký.'),
    ]


class AcademicCourseRegistrationCategory(models.Model):
    """Tầng 2 - Diện đăng ký ÁP DỤNG cho ĐÚNG 1 khóa học cụ thể, với chính sách RIÊNG
    của khóa đó (% giảm, mô tả ưu đãi, mẫu hồ sơ, giá sớm). Đây là màn hình Quản lý thao
    tác hàng ngày (tab "Diện đăng ký" trên form Khóa học) - khóa nào không có dòng cho 1
    loại diện thì loại đó KHÔNG xuất hiện ở form đăng ký của khóa đó.
    """
    _name = 'academic.course.registration.category'
    _description = 'Diện đăng ký áp dụng cho khóa học'
    _order = 'sequence, id'

    course_id = fields.Many2one(
        'academic.course', string='Khóa học', required=True, ondelete='cascade',
    )
    category_id = fields.Many2one(
        'seroto.registration.category', string='Loại diện', required=True,
    )
    # related, store=True: tiện dùng trong domain ẩn/hiện field trên Phiếu đăng ký
    # (VD invisible="category_code != 'voucher'") thay vì phải viết 2 lớp
    # "category_id.category_id.code".
    category_code = fields.Selection(related='category_id.code', store=True, string='Mã kỹ thuật')
    requires_review = fields.Boolean(related='category_id.requires_review', string='Cần duyệt hồ sơ')
    requires_upload = fields.Boolean(related='category_id.requires_upload', string='Yêu cầu chứng từ')

    discount_percent = fields.Float(
        string='% giảm học phí', default=0.0,
        help='0 = đóng đủ học phí, 100 = miễn phí hoàn toàn. Áp lên giá bán hiện tại của '
             'Sản phẩm liên kết của khóa này. Không áp dụng nếu đang còn hạn giá sớm '
             '(xem 2 field Giá sớm bên dưới).',
    )
    description = fields.Html(
        string='Mô tả ưu đãi',
        help='Hiển thị ngay trên form đăng ký website khi khách chọn diện này ở khóa học này.',
    )
    template_link = fields.Char(
        string='Link mẫu tải về',
        help='Link file mẫu KHÔNG lưu trong phần mềm (VD Google Drive), riêng cho khóa '
             'học này - chỉ có ý nghĩa khi Loại diện yêu cầu chứng từ.',
    )

    # Chỉ có ý nghĩa với dòng "Đóng học phí" - còn hạn thì DÙNG THẲNG giá này (bỏ qua %
    # giảm ở trên), hết hạn hoặc để trống thì rơi về công thức % giảm bình thường.
    early_bird_deadline = fields.Date(string='Ngày kết thúc giá sớm')
    early_bird_price = fields.Float(string='Học phí giá sớm')

    sequence = fields.Integer(default=10)
    active = fields.Boolean(
        default=True,
        help='Tắt để tạm ẩn diện này khỏi form đăng ký của khóa mà không phải xóa cấu hình.',
    )

    _sql_constraints = [
        ('course_category_uniq', 'unique(course_id, category_id)',
         'Khóa học này đã có sẵn 1 dòng cho đúng loại diện này rồi.'),
    ]

    def _resolve_final_price(self, base_price):
        """Học phí thực áp dụng cho 1 lượt đăng ký - còn hạn giá sớm thì dùng thẳng giá
        sớm (bỏ qua % giảm), hết hạn/không có giá sớm thì lấy base_price x (1 - % giảm).
        base_price truyền vào từ ngoài (course_id.product_id.list_price) - không tự đọc
        lại ở đây để hàm này dùng lại được cho cả trường hợp xem trước giá (chưa chắc đã
        có course_id.product_id nếu gọi từ nơi khác).
        """
        self.ensure_one()
        today = fields.Date.context_today(self)
        if self.early_bird_deadline and self.early_bird_price and today <= self.early_bird_deadline:
            return self.early_bird_price
        return base_price * (1 - (self.discount_percent or 0.0) / 100.0)


class AcademicCourse(models.Model):
    _inherit = 'academic.course'

    registration_category_line_ids = fields.One2many(
        'academic.course.registration.category', 'course_id', string='Diện đăng ký',
    )
