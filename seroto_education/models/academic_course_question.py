# -*- coding: utf-8 -*-

from odoo import models, fields


class AcademicCourseQuestion(models.Model):
    _name = 'academic.course.question'
    _description = 'Câu hỏi chuyên sâu (khóa học)'
    _order = 'sequence, id'

    course_id = fields.Many2one(
        'academic.course', string='Khóa học', required=True, ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    question = fields.Char(string='Câu hỏi', required=True)

    # "select"/"radio" đều CHỈ chọn được 1 đáp án - khác nhau ở giao diện hiển thị (dropdown
    # thu gọn / các ô rời click loại trừ nhau, nhãn "radio" vẫn ghi "(Checkbox)" theo đúng
    # cách gọi của người dùng, KHÔNG phải chọn nhiều như tên "checkbox" hay gợi nhầm).
    question_type = fields.Selection(
        [
            ('text', 'Văn bản tự do'),
            ('select', 'Chọn 1 đáp án (Dropdown)'),
            ('radio', 'Chọn 1 đáp án (Checkbox)'),
        ],
        string='Loại câu hỏi', default='text', required=True,
    )
    # Chỉ có ý nghĩa khi question_type là select/radio - MỖI LỰA CHỌN 1 DÒNG (không
    # dùng dấu phẩy, tránh đụng lựa chọn tự nó chứa dấu phẩy). Website (JS) tự tách theo
    # dòng để dựng dropdown/nhóm ô chọn - xem
    # vtt_seroto_website: SerotoCourseRegistration._get_course_questions().
    options = fields.Text(
        string='Các lựa chọn',
        help='Mỗi lựa chọn 1 dòng - chỉ áp dụng khi Loại câu hỏi là Chọn 1 đáp án (Dropdown/Checkbox).',
    )

    # Cho phép mỗi "Diện đăng ký" của cùng 1 khóa học có bộ câu hỏi chuyên sâu RIÊNG -
    # danh sách value PHẢI khớp y hệt seroto.course.registration.registration_category
    # (module vtt_seroto_website). CỐ TÌNH khai lại thay vì tham chiếu chéo - module này
    # không (và không nên) phụ thuộc vtt_seroto_website, đúng chiều phụ thuộc hiện tại
    # (vtt_seroto_website mới là bên tự tra academic.course qua self.env, xem
    # SerotoCourseRegistration._get_course_questions()), giống cách CATEGORY_INFO_LABELS
    # đã bị khai trùng có chủ đích giữa model/controller bên đó.
    registration_category = fields.Selection(
        [
            ('tuition', 'Diện đóng học phí'),
            ('voucher', 'Diện voucher quà tặng'),
            ('education_scholarship', 'Diện học bổng giáo dục'),
            ('medical_scholarship', 'Diện học bổng ngành y'),
            ('nonprofit', 'Diện tổ chức phi lợi nhuận'),
        ],
        string='Diện đăng ký',
        help='Chỉ áp dụng khi KHÔNG đánh dấu "Dùng chung" bên dưới.',
    )
    # default=True để MỌI câu hỏi đã cấu hình từ trước (chưa từng biết tới "diện") tự
    # động coi là dùng chung ngay sau khi nâng cấp module - không mất hiển thị đột ngột
    # ở bất kỳ diện đăng ký nào.
    is_shared = fields.Boolean(
        string='Dùng chung', default=True,
        help='Hiển thị cho MỌI diện đăng ký. Bỏ chọn để giới hạn theo đúng 1 diện cụ thể.',
    )
