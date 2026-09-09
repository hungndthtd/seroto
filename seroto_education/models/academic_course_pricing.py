# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

# Danh sách "Diện đăng ký" - PHẢI khớp y hệt seroto.course.registration.registration_category
# (module vtt_seroto_website, không phụ thuộc ngược lại module này - xem comment tại
# academic_course_question.py, cùng quy ước khai trùng có chủ đích).
REGISTRATION_CATEGORY_SELECTION = [
    ('tuition', 'Diện đóng học phí'),
    ('voucher', 'Diện voucher quà tặng'),
    ('education_scholarship', 'Diện học bổng giáo dục'),
    ('medical_scholarship', 'Diện học bổng ngành y'),
    ('nonprofit', 'Diện tổ chức phi lợi nhuận'),
]

# 3 diện dùng chung kiểu giá trị "Mức giảm học phí (%)" - mỗi DÒNG ở đây đã tự gắn với
# ĐÚNG 1 diện duy nhất (course_id + registration_category), nên dùng chung 1 field
# discount_percent KHÔNG còn bị lẫn giữa 2 diện học bổng khác nhau như lúc còn để 3
# field riêng thẳng trên academic.course.
DISCOUNT_PERCENT_CATEGORIES = ('education_scholarship', 'medical_scholarship', 'nonprofit')


class AcademicCoursePricing(models.Model):
    _name = 'academic.course.pricing'
    _description = 'Cấu hình giá theo diện đăng ký (Khóa học)'
    _order = 'course_id, sequence, id'

    sequence = fields.Integer(default=10)

    # 5 dòng tự sinh (1 dòng/diện) ngay lúc TẠO Khóa học (xem AcademicCourse.create())
    # - nhưng khóa học đã có từ TRƯỚC khi module này cài (DB khác, hoặc nâng cấp module
    # trên DB cũ) sẽ KHÔNG tự có 5 dòng này (create() chỉ chạy lúc tạo mới) - cho phép
    # nhân viên tự thêm/xóa (create=true/delete=true trên view) để tự bổ sung khi cần,
    # KHÔNG còn cố định cứng như trước. _course_category_uniq bên dưới chặn tạo trùng 2
    # dòng cùng diện cho 1 khóa học - nếu trùng, mọi chỗ đọc pricing.early_price/
    # discount_percent (vtt_seroto_website, giả định LUÔN đúng 1 dòng khớp diện) sẽ vỡ
    # với lỗi "Expected singleton" ngay khi khách đăng ký đúng diện đó.
    course_id = fields.Many2one(
        'academic.course', string='Khóa học', required=True, ondelete='cascade',
    )
    _course_category_uniq = models.Constraint(
        'unique(course_id, registration_category)',
        'Mỗi diện đăng ký chỉ được cấu hình đúng 1 dòng cho mỗi khóa học.',
    )
    # readonly="id" trên view (không phải readonly=True ở field) - CHO SỬA khi đang tạo
    # dòng mới (chưa có id), KHÓA lại sau khi đã lưu - tránh đổi diện của 1 dòng đã có
    # sẵn dữ liệu (early_price/discount_percent) làm lẫn sang diện khác ngoài ý muốn.
    registration_category = fields.Selection(
        REGISTRATION_CATEGORY_SELECTION, string='Diện đăng ký', required=True,
    )
    # Mặc định False (CỐ TÌNH, đổi từ True trước đây) - dòng diện mới sinh ra (tự động lúc
    # tạo Khóa học, hoặc nhân viên tự thêm) BẮT BUỘC phải được bật tay mới hiện lên form
    # đăng ký website. Mục đích: nhắc nhân viên phải vào cấu hình giá/ưu đãi (early_price/
    # discount_percent) cho ĐÚNG diện đó trước khi cho khách chọn - tránh trường hợp khách
    # đăng ký nhằm 1 diện chưa cấu hình gì (early_price/discount_percent = 0) mà không
    # nhận được ưu đãi nào cả, không phát hiện ra cho tới khi khách phản ánh. Quản lý tắt
    # dòng nào thì diện đó KHÔNG còn xuất hiện trên form đăng ký website CỦA ĐÚNG khóa
    # này nữa (không xóa cấu hình % đã nhập, chỉ ẩn) - xem controllers/
    # academic_course_snippet.py (module vtt_seroto_website), academic_course_is_registration_open.
    # CỐ TÌNH đặt tên "website_visible" (KHÔNG dùng tên field mặc định "active" của Odoo)
    # - "active" mang ý nghĩa đặc biệt trong ORM (tự bị loại khỏi mọi search()/browse()
    # mặc định, kể cả đọc qua One2many như course_id.pricing_ids trong Python), tắt nó đi
    # sẽ làm dòng cấu hình "biến mất" luôn khỏi tab Cấu hình giá trên form Khóa học lẫn
    # _onchange_registration_category_pricing() (module vtt_seroto_website, đọc pricing
    # theo diện lúc nhân viên tạo Phiếu tay ở backend) - trong khi ý định thật của field
    # này CHỈ là ẩn/hiện trên FORM ĐĂNG KÝ WEBSITE, không phải lưu trữ/xóa mềm bản ghi.
    website_visible = fields.Boolean(
        string='Hiển thị trên website', default=False,
        help='Bật lên để cho diện này xuất hiện trên form đăng ký của khóa học này - nhớ '
             'nhập đủ cấu hình giá/ưu đãi trước khi bật, tránh khách đăng ký mà không có '
             'ưu đãi nào.',
    )
    content = fields.Char(
        string='Nội dung',
        help='Mô tả ngắn về ưu đãi này (hiển thị nội bộ cho nhân viên, không hiện cho khách).',
    )
    # currency_id CHỈ để early_price hiện đúng đơn vị tiền tệ - luôn theo tiền tệ công ty
    # (cùng quy ước với academic.course.currency_id).
    currency_id = fields.Many2one(
        'res.currency', string='Đơn vị tiền tệ', related='course_id.currency_id',
    )
    # --- Field giá trị THẬT - chỉ 1 trong 3 nhóm dưới đây có ý nghĩa, tùy
    # registration_category của ĐÚNG dòng này (ẩn/hiện qua view, xem academic_course_views.xml) ---
    early_price = fields.Monetary(
        string='Mức học phí đăng ký sớm', currency_field='currency_id',
        help='Áp dụng cho Diện đóng học phí khi Phiếu đăng ký chọn "Đăng ký sớm".',
    )
    discount_percent = fields.Float(
        string='Mức giảm học phí (%)',
        help='Áp dụng mặc định cho diện này khi tạo Phiếu đăng ký - nhân viên vẫn sửa '
             'được riêng trên từng phiếu.',
    )

    # Cột "Ưu đãi" hiển thị trên list - CHỈ ĐỂ XEM (không nhập trực tiếp vào đây được vì
    # các diện có KIỂU DỮ LIỆU thật khác nhau - tiền/%, không gộp chung 1 field vừa nhập
    # vừa giữ đúng kiểu). Muốn sửa số thật, bấm vào dòng để mở form riêng (xem <form>
    # lồng trong <field name="pricing_ids"> của academic_course_views.xml). Diện voucher
    # không có gì để hiển thị ở đây - chương trình/mã áp dụng cấu hình thẳng ở
    # loyalty.reward (Sales > Chiết khấu & Khách hàng thân thiết), không cấu hình lại ở
    # màn này (đã bỏ field loyalty_program_id trước đây do không có tác dụng thật, chỉ
    # gây hiểu lầm là "gắn" được voucher vào khóa từ đây).
    offer_display = fields.Char(string='Ưu đãi', compute='_compute_offer_display')

    @api.depends('registration_category', 'early_price', 'discount_percent')
    def _compute_offer_display(self):
        for rec in self:
            if rec.registration_category == 'tuition':
                rec.offer_display = (
                    '{:,.0f}đ'.format(rec.early_price).replace(',', '.')
                    if rec.early_price else ''
                )
            elif rec.registration_category in DISCOUNT_PERCENT_CATEGORIES:
                rec.offer_display = '%s%%' % rec.discount_percent if rec.discount_percent else ''
            else:
                rec.offer_display = ''

    # Chặn cứng NGOÀI khoảng 0-100 - đã gặp thực tế nhân viên gõ nhầm số quá lớn (VD
    # 4000) làm _get_payment_amount() (module vtt_seroto_website) ra số tiền ÂM.
    @api.constrains('discount_percent')
    def _check_discount_percent_range(self):
        for rec in self:
            if not (0 <= rec.discount_percent <= 100):
                raise ValidationError(_('Mức giảm học phí (%) phải nằm trong khoảng 0-100.'))
