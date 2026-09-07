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
    _order = 'course_id, id'

    # 5 dòng CỐ ĐỊNH/tự sinh (1 dòng/diện) ngay lúc tạo Khóa học (xem
    # AcademicCourse.create()) - KHÔNG cho thêm/xóa tay (create="false" delete="false"
    # trên view) để tránh trùng/thiếu diện.
    course_id = fields.Many2one(
        'academic.course', string='Khóa học', required=True, ondelete='cascade',
    )
    registration_category = fields.Selection(
        REGISTRATION_CATEGORY_SELECTION, string='Diện đăng ký', required=True, readonly=True,
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
    # CHỈ mang tính tham chiếu/điều hướng nhanh cho nhân viên (bấm mở thẳng Phiếu giảm
    # giá của khóa) - KHÔNG dùng để validate mã voucher, việc đó vẫn theo đúng phạm vi
    # sản phẩm cấu hình trong loyalty.reward (xem
    # SerotoCourseRegistration._validate_voucher_code, module vtt_seroto_website).
    loyalty_program_id = fields.Many2one(
        'loyalty.program', string='Phiếu giảm giá tương ứng',
        help='Chỉ để tham chiếu nhanh - không ảnh hưởng việc kiểm tra mã voucher.',
    )
    discount_percent = fields.Float(
        string='Mức giảm học phí (%)',
        help='Áp dụng mặc định cho diện này khi tạo Phiếu đăng ký - nhân viên vẫn sửa '
             'được riêng trên từng phiếu.',
    )

    # Cột "Ưu đãi" hiển thị trên list - CHỈ ĐỂ XEM (không nhập trực tiếp vào đây được vì
    # 3 diện có 3 KIỂU DỮ LIỆU thật khác nhau - tiền/link/%, không gộp chung 1 field vừa
    # nhập vừa giữ đúng kiểu). Muốn sửa số/liên kết thật, bấm vào dòng để mở form riêng
    # (xem <form> lồng trong <field name="pricing_ids"> của academic_course_views.xml).
    offer_display = fields.Char(string='Ưu đãi', compute='_compute_offer_display')

    @api.depends('registration_category', 'early_price', 'loyalty_program_id.name', 'discount_percent')
    def _compute_offer_display(self):
        for rec in self:
            if rec.registration_category == 'tuition':
                rec.offer_display = (
                    '{:,.0f}đ'.format(rec.early_price).replace(',', '.')
                    if rec.early_price else ''
                )
            elif rec.registration_category == 'voucher':
                rec.offer_display = rec.loyalty_program_id.name or ''
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
