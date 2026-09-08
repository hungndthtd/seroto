# -*- coding: utf-8 -*-

from odoo import models, fields


class AcademicRegistrationCategory(models.Model):
    _name = 'academic.registration.category'
    _description = 'Diện đăng ký (danh mục dùng chung)'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    # PHẢI khớp y hệt value của seroto.course.registration.registration_category (module
    # vtt_seroto_website, không phụ thuộc ngược - xem comment tại academic_course_question.py)
    # - dùng để so khớp diện bằng CHUỖI, không dùng id (id phụ thuộc thứ tự tạo data, dễ
    # lệch giữa các DB khác nhau).
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)

    # 1 NGUỒN SỰ THẬT DUY NHẤT cho "diện nào cần duyệt/upload" - trước đây hardcode rải
    # rác thành nhiều tuple/list riêng ở cả Python (vtt_seroto_website) lẫn JS
    # (course_register_wizard.js), thêm/sửa 1 diện phải sửa nhiều chỗ, dễ bỏ sót. Giờ
    # SerotoCourseRegistration._requires_category_confirmation()/_requires_category_upload()
    # (module vtt_seroto_website) và JS đều đọc lại đúng 2 field này qua RPC (xem
    # controllers/academic_course_snippet.py, academic_course_is_registration_open).
    requires_review = fields.Boolean(
        string='Cần nhân viên duyệt hồ sơ trước khi thanh toán',
        help='Khách nộp hồ sơ xong CHƯA có link thanh toán - chờ Sale/Quản lý bấm '
             '"Xác nhận thông tin đăng ký" mới tạo link/áp mức giảm.',
    )
    requires_upload = fields.Boolean(string='Yêu cầu tải lên chứng từ')
    # Link file mẫu (Google Drive/website...) cho khách TẢI VỀ, điền/ký rồi đính kèm lại
    # qua khối "upload" (chỉ hiện khi requires_upload=True, xem course_register_wizard.js
    # _onCategoryChange) - trước đây <a id="wizard_category_template_link"> luôn để
    # href="#" (KHÔNG có link thật), JS chỉ ẩn/hiện cứng theo 2 mã diện hardcode
    # (education_scholarship/nonprofit). Để trống thì KHÔNG hiện link (diện đó chưa có
    # mẫu sẵn, khách tự chuẩn bị giấy tờ - VD diện học bổng ngành y).
    template_url = fields.Char(
        string='Link mẫu giấy tờ',
        help='Link tải mẫu giấy tờ (VD Google Drive) hiện kèm khối đính kèm trên form '
             'đăng ký website - để trống nếu diện này chưa có mẫu sẵn.',
    )

    _code_uniq = models.Constraint('unique(code)', 'Mã diện đăng ký không được trùng.')
