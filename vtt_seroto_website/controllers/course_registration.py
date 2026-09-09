import json
import logging

from odoo import http, fields, _
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import consteq

_logger = logging.getLogger(__name__)


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

    def _prepare_registration_vals(
        self, *, course, name, email, phone, student_relation, student_name,
        has_studied_seroto_before, registration_category, commitment_confirmed,
        early_registration_status, voucher_type, voucher_code,
        medical_facility_name, medical_facility_province, medical_role,
        nonprofit_org_name, nonprofit_org_province, nonprofit_org_ward,
        nonprofit_registrant_role, nonprofit_signer_name, nonprofit_signer_phone,
        nonprofit_representative_name, nonprofit_representative_phone,
        basic_answers=None,
    ):
        """Validate toàn bộ "Thông tin cơ bản" + "Diện đăng ký" và dựng vals - dùng CHUNG
        cho cả tạo phiếu mới (create_registration) lẫn sửa lại phiếu đã tồn tại
        (update_basic_registration). Trả về vals (dict) - KHÔNG create()/write() ở đây,
        để 2 route tự quyết định gọi cách nào.

        CỐ TÌNH bắt buộc gọi bằng keyword (dấu * ngăn truyền theo vị trí) - 23 tham số
        cùng kiểu str dễ truyền NHẦM THỨ TỰ mà Python không báo lỗi gì (đã xảy ra thực tế
        1 lần khi viết update_basic_registration), keyword argument buộc phải ghi rõ tên
        từng cái, tự loại bỏ hẳn khả năng nhầm vị trí.
        """
        course = (course or '').strip()
        name = (name or '').strip()
        email = (email or '').strip()
        phone = (phone or '').strip()
        student_relation = (student_relation or 'self').strip()
        student_name = (student_name or '').strip()
        registration_category = (registration_category or 'tuition').strip()

        if not (course and name and email and phone):
            raise UserError(_('Vui lòng điền đầy đủ thông tin cơ bản.'))
        if student_relation != 'self' and not student_name:
            raise UserError(_('Vui lòng nhập họ tên học viên.'))
        # ĐÃ BỎ ràng buộc chặn cứng "commitment_confirmed" (field vẫn còn trong model để
        # tương thích ngược, xem vals bên dưới) - không còn field riêng nào trên form
        # nữa, giao hẳn cho từng Khóa học TỰ cấu hình câu hỏi cam kết (nếu cần) qua "Câu
        # hỏi cơ bản" loại Checkbox (academic.course.basic.question, module
        # seroto_education) - đã validate đủ ở đoạn basic_answers bên dưới, khóa nào
        # KHÔNG cấu hình câu hỏi cam kết thì không còn bắt buộc gì thêm.

        # Diện học bổng ngành y/tổ chức phi lợi nhuận - bắt buộc đủ field riêng của diện
        # đó (trước đây thiếu field nào cũng ÂM THẦM bỏ qua, không báo lỗi gì - xem
        # category_info_labels bên dưới, chỉ lọc bỏ giá trị rỗng chứ không chặn). Diện
        # học bổng giáo dục KHÔNG có field text riêng (chỉ cần giấy tờ, xem
        # CATEGORY_INFO_LABELS bên models/course_registration.py) nên không nằm trong
        # danh sách này - giấy tờ đính kèm validate riêng ở 2 route gọi hàm này
        # (create_registration/update_basic_registration, cần biết attachments/trạng
        # thái phiếu cũ nên không kiểm ở đây được).
        required_fields_by_category = {
            'medical_scholarship': [medical_facility_name, medical_facility_province, medical_role],
            'nonprofit': [
                nonprofit_org_name, nonprofit_org_province, nonprofit_org_ward,
                nonprofit_registrant_role, nonprofit_signer_name, nonprofit_signer_phone,
                nonprofit_representative_name, nonprofit_representative_phone,
            ],
        }
        for value in required_fields_by_category.get(registration_category, []):
            if not (value or '').strip():
                raise UserError(_('Vui lòng điền đầy đủ thông tin theo diện đăng ký.'))

        # "Câu hỏi cơ bản" (Bước 1, module seroto_education) - bắt buộc trả lời đủ mọi
        # câu ÁP DỤNG cho ĐÚNG diện vừa chọn (is_shared/khớp diện, xem models/
        # course_registration.py _get_applicable_basic_questions) - "required" phía JS
        # chỉ là UX, khách vẫn gọi thẳng route này bỏ qua giao diện được.
        basic_answers = basic_answers or []
        answered_basic = {
            (item.get('question') or '').strip(): (item.get('answer') or '').strip()
            for item in basic_answers
        }
        applicable_basic_questions = request.env['seroto.course.registration']._get_applicable_basic_questions(
            course, registration_category,
        )
        for q in applicable_basic_questions:
            if not answered_basic.get(q['question']):
                raise UserError(_('Vui lòng trả lời đầy đủ các câu hỏi cơ bản.'))

        # Chặn THẬT ở server, không chỉ ẩn nút "Đăng ký ngay" trên giao diện (nhiều
        # trang landing tĩnh khác của Seroto không kiểm tra is_registration_open trước
        # khi hiện nút) - is_registration_open tự tính theo đúng trạng thái "Lớp nhận
        # đăng ký" của khóa học (xem seroto_education/models/academic_course.py).
        course_record = request.env['academic.course'].sudo().search([('name', '=', course)], limit=1)
        if course_record and not course_record.is_registration_open:
            raise UserError(_('Khóa học "%s" hiện không mở đăng ký.') % course)

        # Diện voucher - validate mã "Phiếu giảm giá" (loyalty.card) NGAY TẠI ĐÂY - mã sai
        # chặn cứng (xem models/course_registration.py, _validate_voucher_code). CHỈ
        # validate + tính học phí sau giảm để tạo đúng link thanh toán - KHÔNG trừ điểm ở
        # đây, điểm chỉ thực sự bị trừ khi Đơn hàng được tạo sau khi thanh toán xong, qua
        # đúng luồng áp mã chuẩn của Odoo (sale_loyalty _try_apply_code, xem
        # models/course_registration.py _create_sale_order()) - nên sửa đi sửa lại mã
        # nhiều lần trước khi thanh toán không tốn/mất điểm gì cả.
        loyalty_card = voucher_discount = voucher_final_amount = False
        if registration_category == 'voucher':
            voucher_code = (voucher_code or '').strip()
            # TRƯỚC ĐÂY: để trống mã vẫn cho qua ÂM THẦM (không validate gì), khách bấm
            # "Tiếp tục" đăng ký được với GIÁ ĐẦY ĐỦ, không có ưu đãi nào - phát hiện thực
            # tế qua phản ánh của khách. Chặn cứng ở đây (không chỉ dựa vào required phía
            # JS, xem course_register_wizard.js) - khách gọi thẳng route này bỏ qua giao
            # diện vẫn bị chặn.
            if not voucher_code:
                raise UserError(_('Vui lòng nhập mã voucher.'))
            base_amount = course_record.product_id.list_price if course_record and course_record.product_id else 0
            loyalty_card, voucher_discount, voucher_final_amount = request.env[
                'seroto.course.registration'
            ]._validate_voucher_code(voucher_code, course_record, base_amount)

        vals = {
            'course_name': course,
            'partner_name': name,
            'email': email,
            'phone': phone,
            'registration_category': registration_category,
            'commitment_confirmed': bool(commitment_confirmed),
            'student_relation': student_relation,
            'student_name': student_name if student_relation != 'self' else False,
            # Diện voucher không còn hợp lệ nữa (đổi qua diện khác lúc SỬA lại) - xóa sạch
            # dữ liệu voucher cũ, không phải chỉ bỏ qua như trước - quan trọng khi CẬP NHẬT
            # (tạo mới thì các field này vốn đã rỗng sẵn, ghi đè không ảnh hưởng gì).
            'loyalty_card_id': False,
            'voucher_discount_amount': 0,
            'voucher_final_amount': 0,
            'early_registration_status': False,
            'voucher_type': False,
            'voucher_code': False,
            # Reset mặc định - nạp lại đúng theo diện bên dưới nếu áp dụng. CẦN có ở
            # đây (không chỉ dựa vào _onchange_registration_category_pricing bên model)
            # vì phiếu tạo/sửa qua WEBSITE đi thẳng qua ORM create()/write(), KHÔNG bao
            # giờ chạy qua @api.onchange (onchange chỉ chạy khi tương tác trên form
            # backend) - thiếu đoạn này thì discount_percent/early_price luôn = 0 dù
            # Khóa học đã cấu hình sẵn mức giảm, đã xảy ra thực tế.
            'early_price': 0,
            'discount_percent': 0,
            # Khách quay lại sửa "Thông tin cơ bản" (update-basic) SAU KHI nhân viên đã
            # xác nhận (category_discount_confirmed=True) - giá trị/giấy tờ có thể đã
            # đổi khác, bắt buộc nhân viên xác nhận LẠI mới mở lại được thanh toán
            # (write() KHÔNG tự chạy qua @api.onchange nên phải reset tường minh ở đây).
            'category_discount_confirmed': False,
        }
        # Diện đóng học phí LUÔN cần 1 giá trị "Trạng thái đăng ký" (field bắt buộc phải
        # có ý nghĩa để tính early_price, xem _get_payment_amount) - mặc định "Đăng ký
        # bình thường", CHỈ đổi thành "Đăng ký sớm" nếu khớp điều kiện bên dưới. TRƯỚC ĐÂY
        # để trống (False) khi không rơi vào diện sớm, hiện trống trên phiếu backend dù
        # field model có default='normal' (default chỉ áp dụng khi THIẾU key trong vals,
        # ở đây vals luôn có key này - xem reset 'early_registration_status': False phía
        # trên) - gán tường minh ở đây, không dựa vào default nữa. Đặt TRƯỚC "if
        # course_record" để vẫn có giá trị 'normal' ngay cả khi không tìm thấy academic.
        # course khớp tên (course_record rỗng, registration_category vẫn mặc định 'tuition').
        if registration_category == 'tuition':
            vals['early_registration_status'] = 'normal'
        if course_record:
            pricing = course_record.pricing_ids.filtered(
                lambda p: p.registration_category == registration_category
            )
            if registration_category == 'tuition':
                vals['early_price'] = pricing.early_price
                # Tự xác định "Đăng ký sớm" - đăng ký TRƯỚC "Ngày mở đăng ký" của Lớp
                # nhận đăng ký (academic.class.registration_open_date, module
                # seroto_education) thì tính sớm - CHỈ để tính giá (early_price), KHÔNG
                # liên quan gì tới việc chặn/mở đăng ký (vẫn đúng 1 nguồn sự thật là
                # "state" của lớp, xem is_registration_open).
                open_date = course_record.default_class_id.registration_open_date
                if open_date and fields.Date.context_today(request.env.user) < open_date:
                    vals['early_registration_status'] = 'early'
            elif registration_category in (
                    'education_scholarship', 'medical_scholarship', 'nonprofit'):
                vals['discount_percent'] = pricing.discount_percent
        if has_studied_seroto_before in ('yes', 'no'):
            vals['has_studied_seroto_before'] = has_studied_seroto_before
        if loyalty_card:
            vals['loyalty_card_id'] = loyalty_card.id
            vals['voucher_discount_amount'] = voucher_discount
            vals['voucher_final_amount'] = voucher_final_amount

        # Diện đóng học phí/voucher - field riêng thật trên model (Selection/Char), JS
        # chỉ gửi lên field của khối đang hiện.
        for key, value in {
            'early_registration_status': early_registration_status,
            'voucher_type': voucher_type,
            'voucher_code': voucher_code,
        }.items():
            if value:
                vals[key] = value.strip() if isinstance(value, str) else value

        # Diện y tế/tổ chức phi lợi nhuận - KHÔNG có field riêng trên model, ghép thành
        # category_info_ids (label/value) để backend hiển thị dạng list editable, y hệt
        # answer_ids/"Câu hỏi chuyên sâu" (xem models/course_registration.py,
        # SerotoCourseRegistrationCategoryInfo). Nhãn cố định theo đúng thứ tự hiển thị
        # mong muốn, không phụ thuộc thứ tự tham số hàm. (5, 0, 0) xóa sạch dòng CŨ trước -
        # an toàn cho cả tạo mới (chưa có dòng nào, no-op) lẫn cập nhật (tránh dòng của
        # diện trước đó còn sót/lặp lại khi khách đổi diện lúc sửa).
        category_info_labels = [
            ('medical_facility_name', 'Tên cơ sở y tế', medical_facility_name),
            ('medical_facility_province', 'Cơ sở y tế thuộc tỉnh/thành phố', medical_facility_province),
            ('medical_role', 'Vai trò', medical_role),
            ('nonprofit_org_name', 'Tên tổ chức', nonprofit_org_name),
            ('nonprofit_org_province', 'Trực thuộc tỉnh/thành phố', nonprofit_org_province),
            ('nonprofit_org_ward', 'Thuộc xã/phường', nonprofit_org_ward),
            ('nonprofit_registrant_role', 'Vai trò của bạn tại tổ chức', nonprofit_registrant_role),
            ('nonprofit_signer_name', 'Họ tên người ký giấy xác nhận', nonprofit_signer_name),
            ('nonprofit_signer_phone', 'Số điện thoại người ký giấy xác nhận', nonprofit_signer_phone),
            ('nonprofit_representative_name', 'Họ tên người đại diện nhóm đăng ký', nonprofit_representative_name),
            ('nonprofit_representative_phone', 'Số điện thoại người đại diện nhóm đăng ký', nonprofit_representative_phone),
        ]
        vals['category_info_ids'] = [(5, 0, 0)] + [
            (0, 0, {'label': label, 'value': value.strip()})
            for _key, label, value in category_info_labels if (value or '').strip()
        ]

        # Câu trả lời "Câu hỏi cơ bản" - GHI ĐÈ TOÀN BỘ mỗi lần gọi ((5,0,0) xóa sạch
        # trước), giống category_info_ids ở trên - an toàn cho cả tạo mới lẫn cập nhật
        # (đổi diện thì bộ câu hỏi áp dụng cũng đổi theo, không giữ lại câu trả lời của
        # diện cũ không còn liên quan).
        vals['basic_answer_ids'] = [(5, 0, 0)] + [
            (0, 0, {'question': q['question'], 'answer': answered_basic.get(q['question'], '')})
            for q in applicable_basic_questions
        ]

        return vals

    def _save_attachments(self, registration, attachments):
        if not attachments:
            return
        # Giới hạn THẬT ở server (không chỉ chặn phía JS trước khi encode base64) - route
        # này public, ai cũng gọi thẳng được nếu biết địa chỉ. (6, 0, ids) THAY THẾ toàn bộ
        # danh sách cũ - đúng ý khi khách chọn lại file khác lúc CẬP NHẬT (không cộng dồn
        # file của diện trước đó không còn phù hợp nữa).
        MAX_FILES, MAX_SIZE = 5, 10 * 1024 * 1024
        if len(attachments) > MAX_FILES:
            raise UserError(_('Chỉ được đính kèm tối đa %s file.') % MAX_FILES)
        for item in attachments:
            # base64 dài hơn khoảng 4/3 lần dữ liệu gốc - đủ để chặn thô trước khi phải
            # decode thật.
            if len(item.get('data') or '') * 3 / 4 > MAX_SIZE:
                raise UserError(_('File "%s" vượt quá 10MB.') % (item.get('filename') or ''))
        created = request.env['ir.attachment'].sudo().create([
            {
                'name': item.get('filename') or 'attachment',
                'datas': item.get('data'),
                'res_model': 'seroto.course.registration',
                'res_id': registration.id,
                'mimetype': item.get('mimetype'),
            }
            for item in attachments if item.get('data')
        ])
        registration.category_attachment_ids = [(6, 0, created.ids)]

    def _build_registration_response(self, registration, course):
        # Tự dọn answer_ids theo đúng bộ câu hỏi áp dụng HIỆN TẠI (thêm câu mới/xóa dòng
        # rỗng đã đổi tên - xem _sync_answer_ids) - NV mở phiếu trên backend ngay sau đó
        # luôn thấy đúng, không cần tự tay kích hoạt onchange mới đồng bộ lại.
        registration._sync_answer_ids()
        category_labels = dict(registration._fields['registration_category'].selection)
        # "Loại voucher" không còn hiển thị cho khách chọn (đã ẩn khỏi form/Phiếu đăng
        # ký - field vẫn còn trong model để tương thích ngược với phiếu cũ, chỉ không
        # còn tham gia label này nữa) - chỉ còn hiện đúng mã đã dùng.
        voucher_label = False
        if registration.registration_category == 'voucher' and registration.loyalty_card_id:
            voucher_label = 'Mã: %s' % registration.voucher_code
        return {
            'id': registration.id,
            'token': registration.access_token,
            'checkout_url': registration._get_checkout_url(),
            'qr_url': registration._get_checkout_qr_url(),
            'questions': registration._get_course_questions(course),
            'code': registration.code,
            'registration_category_label': category_labels.get(registration.registration_category),
            'voucher_label': voucher_label,
            # base_amount (giá gốc)/amount (số tiền THẬT cần thu, đã áp giảm giá/voucher
            # nếu có) tính SẴN ở server, tab "Thanh toán" chỉ hiện lại, không tự tính lại
            # ở JS (tránh sai lệch làm tròn) - discount_amount chỉ để hiện, = hiệu số 2
            # giá trên.
            'base_amount': registration._get_base_amount(),
            'amount': registration._get_payment_amount(),
            # 3 diện cần nộp giấy tờ CHƯA được nhân viên xác nhận - CHƯA có giao dịch
            # thanh toán nào (checkout_url/qr_url rỗng), JS/slip page tự hiện thông báo
            # "đang chờ xác nhận" thay vì QR/nút thay vì hiện trạng thái trống/vỡ.
            'pending_confirmation': (
                registration._requires_category_confirmation()
                and not registration.category_discount_confirmed
                and registration.payment_status != 'paid'
            ),
        }

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
                             student_relation=None, student_name=None,
                             has_studied_seroto_before=None,
                             registration_category=None, commitment_confirmed=None,
                             early_registration_status=None,
                             voucher_type=None, voucher_code=None,
                             medical_facility_name=None, medical_facility_province=None,
                             medical_role=None,
                             nonprofit_org_name=None, nonprofit_org_province=None,
                             nonprofit_org_ward=None, nonprofit_registrant_role=None,
                             nonprofit_signer_name=None, nonprofit_signer_phone=None,
                             nonprofit_representative_name=None,
                             nonprofit_representative_phone=None,
                             attachments=None, basic_answers=None, **post):
        vals = self._prepare_registration_vals(
            course=course, name=name, email=email, phone=phone,
            student_relation=student_relation, student_name=student_name,
            has_studied_seroto_before=has_studied_seroto_before,
            registration_category=registration_category,
            commitment_confirmed=commitment_confirmed,
            early_registration_status=early_registration_status,
            voucher_type=voucher_type, voucher_code=voucher_code,
            medical_facility_name=medical_facility_name,
            medical_facility_province=medical_facility_province,
            medical_role=medical_role,
            nonprofit_org_name=nonprofit_org_name,
            nonprofit_org_province=nonprofit_org_province,
            nonprofit_org_ward=nonprofit_org_ward,
            nonprofit_registrant_role=nonprofit_registrant_role,
            nonprofit_signer_name=nonprofit_signer_name,
            basic_answers=basic_answers,
            nonprofit_signer_phone=nonprofit_signer_phone,
            nonprofit_representative_name=nonprofit_representative_name,
            nonprofit_representative_phone=nonprofit_representative_phone,
        )
        vals['state'] = 'new'
        registration = request.env['seroto.course.registration'].sudo().create(vals)
        self._save_attachments(registration, attachments)

        # Chặn THẬT ở server - diện có requires_upload=True (academic.registration.category)
        # bắt buộc có ÍT NHẤT 1 file đính kèm. Raise ở đây (SAU khi đã create()) vẫn AN
        # TOÀN - lỗi làm cả transaction của request này rollback, phiếu vừa tạo không bị
        # lưu lại nửa vời.
        if registration._requires_category_upload() and not registration.category_attachment_ids:
            raise UserError(_('Vui lòng đính kèm giấy tờ/tài liệu theo diện đăng ký.'))

        # 3 diện cần nộp giấy tờ - CHƯA tạo giao dịch thanh toán ngay, đợi nhân viên
        # bấm "Xác nhận thông tin đăng ký" (action_confirm_category_discount) mới tạo,
        # tránh khách trả tiền theo giá GỐC trước khi nhân viên kịp duyệt giấy tờ/áp
        # đúng mức giảm.
        if not registration._requires_category_confirmation():
            registration._create_payment_transaction()
        registration.action_send_confirmation_email()

        return self._build_registration_response(registration, (course or '').strip())

    # =====================================================
    # Sửa lại "Thông tin cơ bản" + "Diện đăng ký" của phiếu ĐÃ TẠO (khách bấm quay lại
    # bước 1 rồi bấm "Tiếp tục" lần nữa) - GHI ĐÈ lên đúng phiếu cũ (id/token nhận từ
    # this._state sau lần submit đầu tiên, xem course_register_wizard.js _onBasicSubmit)
    # thay vì tạo phiếu MỚI + giao dịch thanh toán MỚI mỗi lần bấm lại, tránh tạo trùng
    # phiếu. An toàn để gọi nhiều lần - voucher (nếu có) CHƯA từng bị trừ điểm ở bước này
    # (xem _prepare_registration_vals) nên đổi/bỏ mã qua lại không tốn/mất điểm gì.
    #
    # Chặn CỨNG nếu phiếu đã thanh toán/đã qua "Mới đăng ký" - không cho đổi ngược thông
    # tin cơ bản/số tiền của 1 giao dịch coi như đã xong.
    # =====================================================
    @http.route(
        '/seroto/course-registration/update-basic',
        type='jsonrpc', auth='public', website=True,
    )
    def update_basic_registration(self, id=None, token=None, course=None, name=None,
                                   email=None, phone=None, student_relation=None,
                                   student_name=None, has_studied_seroto_before=None,
                                   registration_category=None, commitment_confirmed=None,
                                   early_registration_status=None,
                                   voucher_type=None, voucher_code=None,
                                   medical_facility_name=None, medical_facility_province=None,
                                   medical_role=None,
                                   nonprofit_org_name=None, nonprofit_org_province=None,
                                   nonprofit_org_ward=None, nonprofit_registrant_role=None,
                                   nonprofit_signer_name=None, nonprofit_signer_phone=None,
                                   nonprofit_representative_name=None,
                                   nonprofit_representative_phone=None,
                                   attachments=None, basic_answers=None, **post):
        registration = self._get_registration_or_raise(id, token)
        if registration.payment_status == 'paid' or registration.state != 'new':
            raise UserError(_('Phiếu đăng ký đã xử lý xong, không thể sửa lại thông tin.'))

        vals = self._prepare_registration_vals(
            course=course, name=name, email=email, phone=phone,
            student_relation=student_relation, student_name=student_name,
            has_studied_seroto_before=has_studied_seroto_before,
            registration_category=registration_category,
            commitment_confirmed=commitment_confirmed,
            early_registration_status=early_registration_status,
            voucher_type=voucher_type, voucher_code=voucher_code,
            medical_facility_name=medical_facility_name,
            medical_facility_province=medical_facility_province,
            medical_role=medical_role,
            nonprofit_org_name=nonprofit_org_name,
            nonprofit_org_province=nonprofit_org_province,
            nonprofit_org_ward=nonprofit_org_ward,
            nonprofit_registrant_role=nonprofit_registrant_role,
            nonprofit_signer_name=nonprofit_signer_name,
            nonprofit_signer_phone=nonprofit_signer_phone,
            nonprofit_representative_name=nonprofit_representative_name,
            nonprofit_representative_phone=nonprofit_representative_phone,
            basic_answers=basic_answers,
        )
        registration.write(vals)
        self._save_attachments(registration, attachments)

        # Chặn THẬT ở server - diện có requires_upload=True bắt buộc có ÍT NHẤT 1 file
        # đính kèm SAU khi ghi - tính theo trạng thái CUỐI CÙNG (không chỉ file mới gửi
        # lần này), vì _save_attachments giữ nguyên file cũ nếu khách không chọn lại file
        # mới lúc sửa "Thông tin cơ bản".
        if registration._requires_category_upload() and not registration.category_attachment_ids:
            raise UserError(_('Vui lòng đính kèm giấy tờ/tài liệu theo diện đăng ký.'))

        # Học phí có thể đã đổi (khóa học/diện/mã voucher khác) - tạo lại link thanh toán
        # MỚI phản ánh đúng số tiền mới. Giao dịch payOS/giả lập CŨ (chưa thanh toán) bị bỏ
        # lại, không dùng nữa - vô hại, chỉ là dữ liệu thừa không ai trỏ tới. KHÔNG gửi lại
        # email xác nhận (chỉ gửi đúng 1 lần lúc tạo phiếu, tránh spam khách mỗi lần sửa).
        # 3 diện cần nộp giấy tờ - category_discount_confirmed vừa bị reset False ở
        # _prepare_registration_vals, CHƯA tạo giao dịch mới, đợi nhân viên xác nhận lại.
        if not registration._requires_category_confirmation():
            registration._create_payment_transaction()

        return self._build_registration_response(registration, (course or '').strip())

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

        # Tự dọn answer_ids theo đúng bộ câu hỏi áp dụng HIỆN TẠI (thêm câu mới/xóa dòng
        # rỗng đã đổi tên - xem models/course_registration.py, _sync_answer_ids) TRƯỚC
        # khi tính unanswered_questions bên dưới - nếu không, dòng rỗng theo tên CŨ vẫn
        # còn lẫn trong answer_ids dù không ai còn hỏi tên đó nữa.
        registration._sync_answer_ids()

        # Câu hỏi chuyên sâu CHƯA trả lời - hiện thẳng input/select ngay trên trang phiếu
        # để khách điền nốt qua link email, không bắt buộc phải mở lại wizard "Đăng ký
        # ngay". Chỉ có ý nghĩa khi phiếu còn hiệu lực (không rejected/cancelled - xem
        # template, phần Câu hỏi chuyên sâu bị ẩn hẳn ở 2 trạng thái đó).
        questions = registration._get_course_questions(registration.course_name)
        answered = {a.question for a in registration.answer_ids if (a.answer or '').strip()}
        unanswered_questions = [q for q in questions if q['question'] not in answered]

        # Route /seroto/course-registration/update GHI ĐÈ TOÀN BỘ answer_ids mỗi lần gọi
        # (xem update_registration bên trên) - phải gửi kèm các câu đã trả lời từ trước
        # cùng lúc với câu mới điền trên trang này, nếu không sẽ bị mất answer cũ. JS đọc
        # lại giá trị này (data-existing-answers) rồi gộp với câu trả lời mới trước khi
        # gọi update.
        existing_answers_json = json.dumps([
            {'question': a.question, 'answer': a.answer} for a in registration.answer_ids
        ])

        return request.render(
            'vtt_seroto_website.course_registration_slip_page',
            {
                'registration': registration,
                'unanswered_questions': unanswered_questions,
                'existing_answers_json': existing_answers_json,
            },
        )
