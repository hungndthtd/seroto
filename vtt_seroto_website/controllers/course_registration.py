from odoo import http, _
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import consteq


class CourseRegistrationController(http.Controller):

    def _get_registration_or_raise(self, registration_id, token):
        try:
            registration_id = int(registration_id)
        except (TypeError, ValueError):
            registration_id = None

        registration = (
            request.env['seroto.course.registration'].sudo().browse(registration_id).exists()
            if registration_id else request.env['seroto.course.registration']
        )

        if not registration or not token or not consteq(registration.access_token, token):
            raise UserError(_('Phiếu đăng ký không hợp lệ hoặc đã bị xóa.'))

        return registration

    # =====================================================
    # Tab "Thông tin cơ bản" hoàn tất -> tạo Phiếu đăng ký khóa học + link thanh toán
    # payOS thật (xem models/course_registration.py _create_payment_transaction) + gửi
    # email kèm link phiếu. CHƯA đụng tới crm.lead/partner - đây là model riêng, độc lập
    # với flow đăng ký cũ (seroto_form).
    # =====================================================
    @http.route(
        '/seroto/course-registration/create',
        type='jsonrpc', auth='public', website=True,
    )
    def create_registration(self, course=None, name=None, email=None, phone=None,
                             student_relation=None, student_name=None, **post):
        course = (course or '').strip()
        name = (name or '').strip()
        email = (email or '').strip()
        phone = (phone or '').strip()
        student_relation = (student_relation or 'self').strip()
        student_name = (student_name or '').strip()

        if not (course and name and email and phone):
            raise UserError(_('Vui lòng điền đầy đủ thông tin cơ bản.'))
        if student_relation != 'self' and not student_name:
            raise UserError(_('Vui lòng nhập họ tên học viên.'))

        vals = {
            'course_name': course,
            'partner_name': name,
            'email': email,
            'phone': phone,
            'state': 'new',
        }
        if student_relation != 'self':
            vals['student_relation'] = student_relation
            vals['student_name'] = student_name

        registration = request.env['seroto.course.registration'].sudo().create(vals)

        registration._create_payment_transaction()
        registration.action_send_confirmation_email()

        return {
            'id': registration.id,
            'token': registration.access_token,
            'checkout_url': registration._get_checkout_url(),
            'qr_url': registration._get_checkout_qr_url(),
            'questions': registration._get_course_questions(course),
        }

    # =====================================================
    # Đọc trạng thái thanh toán hiện tại - JS ở tab "Thanh toán" gọi định kỳ (polling)
    # trong lúc chờ payOS gọi webhook báo kết quả (route cố định /payos/webhook, module
    # vtt_payos - xem models/course_registration.py, _payos_on_paid).
    # =====================================================
    @http.route(
        '/seroto/course-registration/status',
        type='jsonrpc', auth='public', website=True,
    )
    def registration_status(self, id=None, token=None, **post):
        registration = self._get_registration_or_raise(id, token)
        return {'payment_status': registration.payment_status}

    # =====================================================
    # Cập nhật Thông tin chuyên sâu (tab 3) của 1 phiếu đã tạo - dùng chung cho cả modal
    # wizard lẫn trang xem phiếu qua link email. "answers" là danh sách
    # [{question, answer}, ...] - câu hỏi lấy từ registration._get_course_questions()
    # (khớp theo khóa học), ghi đè toàn bộ answer_ids cũ mỗi lần gọi (khách có thể sửa
    # lại câu trả lời trước khi bấm "Hoàn tất đăng ký").
    #
    # LƯU Ý: route này KHÔNG nhận payment_status từ client - trạng thái thanh toán chỉ
    # đổi qua webhook payOS (xác thực bằng chữ ký, không thể giả mạo từ trình duyệt
    # khách) thay vì client tự khai như bản mô phỏng trước đó.
    # =====================================================
    @http.route(
        '/seroto/course-registration/update',
        type='jsonrpc', auth='public', website=True,
    )
    def update_registration(self, id=None, token=None, answers=None, **post):
        registration = self._get_registration_or_raise(id, token)

        if answers is not None:
            registration.answer_ids.unlink()
            request.env['seroto.course.registration.answer'].sudo().create([
                {
                    'registration_id': registration.id,
                    'question': (item.get('question') or '').strip(),
                    'answer': (item.get('answer') or '').strip(),
                }
                for item in answers if (item.get('question') or '').strip()
            ])

        return {
            'success': True,
            'payment_status': registration.payment_status,
        }

    # =====================================================
    # Trang xem "Phiếu đăng ký khóa học" từ link trong email - public, xác thực bằng
    # access_token trong URL (không cần đăng nhập).
    # =====================================================
    @http.route(
        '/dang-ky-khoa-hoc/phieu/<int:reg_id>/<string:token>',
        type='http', auth='public', website=True, sitemap=False,
    )
    def view_registration_slip(self, reg_id, token, **kwargs):
        registration = request.env['seroto.course.registration'].sudo().browse(reg_id).exists()

        if not registration or not consteq(registration.access_token, token):
            return request.not_found()

        return request.render(
            'vtt_seroto_website.course_registration_slip_page',
            {'registration': registration},
        )
