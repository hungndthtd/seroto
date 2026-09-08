# -*- coding: utf-8 -*-

from odoo import models, fields


class AcademicCourseBasicQuestion(models.Model):
    _name = 'academic.course.basic.question'
    _description = 'Câu hỏi cơ bản (khóa học)'
    _order = 'sequence, id'

    # Model RIÊNG với academic.course.question ("Câu hỏi chuyên sâu") theo đúng yêu cầu -
    # câu hỏi ở đây hiển thị NGAY Ở BƯỚC 1 "Thông tin cơ bản" của wizard đăng ký (module
    # vtt_seroto_website), TRƯỚC KHI Phiếu đăng ký được tạo - khác hẳn "Câu hỏi chuyên
    # sâu" chỉ hiện SAU khi đã có Phiếu (Bước 3). Cấu trúc field giống hệt (cố ý, để dễ
    # đối chiếu) nhưng KHÔNG dùng chung model/bảng.
    course_id = fields.Many2one(
        'academic.course', string='Khóa học', required=True, ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    question = fields.Char(string='Câu hỏi', required=True)

    # "select"/"radio" đều CHỈ chọn được 1 đáp án TRONG NHIỀU lựa chọn (khai ở "options"
    # bên dưới) - khác hẳn "checkbox" (MỚI, riêng cho tab này) là 1 ô tích ĐỒNG Ý/KHÔNG
    # duy nhất, không cần khai lựa chọn gì thêm - CHÍNH câu hỏi (question) đóng vai trò
    # nhãn của ô tích đó, giống hệt checkbox "Tôi cam kết thông tin đăng ký..." đã có sẵn
    # (hard-code) trên form - đổi tên nhãn "radio" từ "(Checkbox)" cũ sang tên khác để
    # khỏi nhầm với loại "checkbox" thật mới này.
    question_type = fields.Selection(
        [
            ('text', 'Văn bản tự do'),
            ('select', 'Chọn 1 đáp án (Dropdown)'),
            ('radio', 'Chọn 1 đáp án (Nhiều lựa chọn rời)'),
            ('checkbox', 'Đồng ý/Xác nhận (Checkbox)'),
        ],
        string='Loại câu hỏi', default='text', required=True,
    )
    options = fields.Text(
        string='Các lựa chọn',
        help='Mỗi lựa chọn 1 dòng - chỉ áp dụng khi Loại câu hỏi là Chọn 1 đáp án (Dropdown/Nhiều lựa chọn rời).',
    )

    # Cho phép mỗi "Diện đăng ký" có bộ câu hỏi cơ bản RIÊNG, y hệt cơ chế đã làm cho
    # "Câu hỏi chuyên sâu" (academic.registration.category.code khớp với
    # seroto.course.registration.registration_category, module vtt_seroto_website).
    # Tên bảng quan hệ CHỈ ĐỊNH TAY - tên tự sinh mặc định (ghép đủ 2 tên model) dài hơn
    # giới hạn 63 ký tự của Postgres, gây lỗi "Table name is too long" lúc cài đặt.
    registration_category_ids = fields.Many2many(
        'academic.registration.category',
        'academic_course_basic_question_category_rel',
        'basic_question_id', 'category_id',
        string='Diện đăng ký',
        help='Chỉ áp dụng khi KHÔNG đánh dấu "Dùng chung" bên dưới - chọn được nhiều diện.',
    )
    is_shared = fields.Boolean(
        string='Dùng chung', default=True,
        help='Hiển thị cho MỌI diện đăng ký. Bỏ chọn để giới hạn theo đúng 1 hoặc nhiều diện cụ thể.',
    )
