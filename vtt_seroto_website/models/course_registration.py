import logging
import secrets

from markupsafe import Markup

from odoo import api, models, fields, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import formataddr

_logger = logging.getLogger(__name__)

# Nhãn cố định của category_info_ids theo từng diện cần "thông tin điền thêm" - dùng
# chung cho _onchange_registration_category (tự dựng lại khi NHÂN VIÊN đổi diện trên
# backend) VÀ đối chiếu với đúng thứ tự/nội dung controllers/course_registration.py
# đang tạo lúc khách đăng ký qua website (2 nơi phải khớp nhau nếu sau này đổi chữ).
CATEGORY_INFO_LABELS = {
    'medical_scholarship': [
        'Tên cơ sở y tế',
        'Cơ sở y tế thuộc tỉnh/thành phố',
        'Vai trò',
    ],
    'nonprofit': [
        'Tên tổ chức',
        'Trực thuộc tỉnh/thành phố',
        'Thuộc xã/phường',
        'Vai trò của bạn tại tổ chức',
        'Họ tên người ký giấy xác nhận',
        'Số điện thoại người ký giấy xác nhận',
        'Họ tên người đại diện nhóm đăng ký',
        'Số điện thoại người đại diện nhóm đăng ký',
    ],
}


class SerotoCourseRegistration(models.Model):
    _name = 'seroto.course.registration'
    _description = 'Phiếu đăng ký khóa học (modal "Đăng ký ngay" nhiều bước)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'code'

    # Mã phiếu THẬT (lưu trữ, đánh index) - gán 1 lần ngay sau create() (xem create()
    # bên dưới, cần có self.id trước mới ghép được chuỗi). Dùng THỐNG NHẤT cho cả hiển
    # thị (_compute_display_name), tìm kiếm (_rec_name -> _name_search mặc định tìm theo
    # field này), lẫn nội dung chuyển khoản gửi payOS (_create_payment_transaction) -
    # trước đây 3 chỗ này tự ghép chuỗi riêng lẻ, có chỗ còn lệch định dạng (có/không có
    # dấu gạch ngang), khó dò ngược từ nội dung chuyển khoản thật ra đúng phiếu vì model
    # này vốn không có field "name" để tìm theo tên như các model khác.
    code = fields.Char(string='Mã phiếu', copy=False, readonly=True, index=True)

    course_name = fields.Char(string='Khóa học', required=True)
    # Many2one thật, tự suy ra từ course_name lúc tạo (xem create()) - để lọc class_id,
    # tự điền lớp nhận đăng ký mặc định, và sau này tạo sale.order.line đúng sản phẩm.
    course_id = fields.Many2one('academic.course', string='Khóa học (liên kết)')
    # Chỉ cho chọn lớp đang "Đang nhận đăng ký" - tránh nhân viên lỡ tay chọn nhầm lớp
    # đã đóng/đã hoàn thành lúc tạo phiếu tay trên backend (domain chỉ áp dụng cho ô
    # chọn trên UI, không chặn giá trị đã có sẵn từ trước hay ghi thẳng qua ORM - luồng
    # website tự gán class_id = course.default_class_id lúc create(), không đi qua ô
    # chọn này nên không bị ảnh hưởng).
    class_id = fields.Many2one(
        'academic.class', string='Lớp học',
        domain="[('course_id', '=', course_id), ('state', '=', 'open')]",
    )
    partner_name = fields.Char(string='Họ tên người đăng ký', required=True)
    email = fields.Char(string='Email', required=True)
    phone = fields.Char(string='Số điện thoại', required=True)
    # Chỉ tạo/gắn res.partner thật lúc NV xác nhận hoặc tạo đơn hàng (action_confirm/
    # action_create_sale_order) - tránh tạo rác liên hệ cho các phiếu bị từ chối/hủy.
    partner_id = fields.Many2one('res.partner', string='Khách hàng', readonly=True, copy=False)

    # Người đăng ký trên web có thể đăng ký hộ người khác (không phân biệt cụ thể quan
    # hệ gì) thay vì luôn là chính người điền form - "self" (mặc định) nghĩa là
    # partner_name/email/phone ở trên CHÍNH LÀ học viên, không cần student_name riêng.
    # "other" thì student_name là học viên thực tế, còn partner_name/email/phone vẫn
    # luôn là người liên hệ (nhận email xác nhận, đứng tên thanh toán) - xem
    # _find_or_create_student_partner() bên dưới.
    student_relation = fields.Selection([
        ('self', 'Bản thân'),
        ('other', 'Người khác'),
    ], string='Đăng ký cho', default='self', required=True)
    student_name = fields.Char(
        string='Họ tên học viên',
        help='Chỉ cần điền khi đăng ký hộ người khác (student_relation = "Người khác").',
    )

    # Khách phải tick trước khi bấm "Tiếp tục" ở bước "Thông tin cơ bản" (chặn cả
    # server-side trong controller, không chỉ dựa vào required phía JS).
    commitment_confirmed = fields.Boolean(string='Đã cam kết thông tin chính xác', copy=False)

    has_studied_seroto_before = fields.Selection([
        ('no', 'Tôi chưa học bất cứ khóa học nào của Seroto'),
        ('yes', 'Tôi đã học'),
    ], string='Bạn đã học các khóa của Seroto trước đây chưa?', default='no')

    # "Diện đăng ký" - phân loại người đăng ký để áp dụng field/hồ sơ khác nhau. Chọn
    # ngay trong bước "Thông tin cơ bản" của wizard (không phải bước riêng) - xem
    # course_register_wizard.js, _onCategoryChange.
    registration_category = fields.Selection([
        ('tuition', 'Diện đóng học phí'),
        ('voucher', 'Diện voucher quà tặng'),
        ('education_scholarship', 'Diện học bổng giáo dục'),
        ('medical_scholarship', 'Diện học bổng ngành y'),
        ('nonprofit', 'Diện tổ chức phi lợi nhuận'),
    ], string='Diện đăng ký', default='tuition', required=True)

    # --- Diện đóng học phí ---
    # CHỈ lưu lựa chọn ở giai đoạn này - CHƯA tự tính lại amount theo mốc thời gian
    # (xem _create_payment_transaction, để nguyên giai đoạn 2 xử lý).
    early_registration_status = fields.Selection([
        ('normal', 'Đăng ký bình thường'),
        ('early', 'Đăng ký sớm'),
    ], string='Trạng thái đăng ký', default='normal')

    # --- Diện voucher quà tặng ---
    voucher_type = fields.Selection([
        ('angelina', 'Voucher từ người phụng sự (Angelina)'),
        ('seroto_course', 'Voucher từ các khóa học của Seroto'),
        ('seroto_talkshow', 'Voucher từ các talkshow của Seroto'),
    ], string='Loại voucher')
    voucher_code = fields.Char(string='Mã voucher')
    # currency_id CHỈ để 2 field Monetary bên dưới tự hiện đúng đơn vị tiền tệ (VNĐ, không
    # số thập phân theo đúng cấu hình res.currency) - không có ý nghĩa đa tiền tệ gì khác,
    # luôn là tiền tệ của công ty.
    currency_id = fields.Many2one(
        'res.currency', string='Tiền tệ', default=lambda self: self.env.company.currency_id,
    )
    # 3 field dưới đây do _validate_voucher_code() tự điền lúc tạo phiếu (controller gọi
    # TRƯỚC create(), xem controllers/course_registration.py) - KHÔNG tính lại ở nơi khác,
    # _create_payment_transaction() chỉ đọc lại voucher_final_amount để tránh sai lệch làm
    # tròn giữa 2 lần tính.
    loyalty_card_id = fields.Many2one(
        'loyalty.card', string='Phiếu giảm giá đã áp dụng', readonly=True, copy=False,
    )
    voucher_discount_amount = fields.Monetary(string='Số tiền được giảm', readonly=True, copy=False)
    voucher_final_amount = fields.Monetary(string='Học phí sau giảm giá', readonly=True, copy=False)

    # --- Diện đóng học phí (đăng ký sớm) / Diện học bổng giáo dục / Diện học bổng ngành
    # y / Diện tổ chức phi lợi nhuận ---
    # Mặc định tự nạp theo cấu hình của Khóa học (academic.course.early_price/
    # default_discount_percent, xem _onchange_registration_category_pricing bên dưới) -
    # nhân viên vẫn sửa được riêng cho từng phiếu này. Diện voucher KHÔNG dùng 2 field
    # này - giữ nguyên loyalty_card_id/voucher_discount_amount/voucher_final_amount ở
    # trên, không đổi gì.
    early_price = fields.Monetary(
        string='Mức học phí đăng ký sớm', copy=False,
        help='Mặc định lấy theo cấu hình Khóa học, nhân viên có thể sửa riêng cho phiếu này.',
    )
    discount_percent = fields.Float(
        string='Mức giảm học phí (%)', copy=False,
        help='Mặc định lấy theo cấu hình Khóa học, nhân viên có thể sửa riêng cho phiếu này.',
    )
    # Chỉ có ý nghĩa với 3 diện cần nộp giấy tờ (education_scholarship/medical_scholarship/
    # nonprofit) - đánh dấu nhân viên ĐÃ kiểm tra giấy tờ/thông tin đăng ký hợp lệ (bấm nút
    # "Xác nhận thông tin đăng ký", xem action_confirm_category_discount()) và ĐÃ tạo lại
    # đúng link/QR thanh toán theo mức giảm hiện tại - không phải trạng thái tổng của cả
    # phiếu (khác hẳn "state").
    category_discount_confirmed = fields.Boolean(
        string='Đã xác nhận giảm học phí', copy=False, readonly=True,
    )

    # Chặn cứng NGOÀI khoảng 0-100 - đã gặp thực tế nhân viên gõ nhầm số quá lớn (VD
    # 4000) làm _get_payment_amount() ra số tiền ÂM (giảm hơn 100% giá gốc), vô lý về
    # nghiệp vụ - giống hệt constraint bên academic.course (3 field nguồn mặc định).
    @api.constrains('discount_percent')
    def _check_discount_percent_range(self):
        for rec in self:
            if not (0 <= rec.discount_percent <= 100):
                raise ValidationError(_('Mức giảm học phí (%) phải nằm trong khoảng 0-100.'))

    @api.onchange('discount_percent')
    def _onchange_discount_percent_reset_confirm(self):
        """Nhân viên sửa lại % giảm SAU KHI đã xác nhận (category_discount_confirmed=True)
        thì phải bấm "Xác nhận thông tin đăng ký" lại mới tạo được link thanh toán mới -
        tự bỏ đánh dấu để tránh link cũ (số tiền cũ) vẫn còn hiệu lực mà tưởng đã đúng.
        """
        for rec in self:
            if rec.category_discount_confirmed:
                rec.category_discount_confirmed = False

    @api.model
    def _validate_voucher_code(self, code, course_record, amount):
        """Validate mã "Phiếu giảm giá" (model loyalty.card chuẩn Odoo, Sales > Chiết khấu &
        Khách hàng thân thiết) và tính học phí sau giảm cho ĐÚNG amount/course_record hiện
        tại. Trả về (loyalty.card, số tiền được giảm, số tiền cuối cùng) hoặc raise UserError
        nếu mã không hợp lệ - gọi TRƯỚC create() để chặn cứng ngay ở bước "Thông tin cơ bản",
        không tạo phiếu với mã sai.

        loyalty.card KHÔNG lưu số tiền giảm trực tiếp - chỉ lưu points (đơn vị đếm lượt đổi
        thưởng), số tiền/% giảm thật nằm ở loyalty.reward. Core Odoo không có sẵn hàm "mã ->
        số tiền giảm" độc lập (chỉ có trong sale_loyalty, gắn chặt sale.order nhiều dòng) nên
        tự tính ở đây - CHỈ hỗ trợ discount_mode 'percent'/'per_order' (đủ cho hình thức
        "Phiếu giảm giá" thủ công), 'per_point' (kiểu ví điểm gift_card/ewallet) chưa hỗ trợ.
        """
        card = self.env['loyalty.card'].sudo().search([('code', '=', code)], limit=1)
        if not card or not card.program_id.active:
            raise UserError(_('Mã voucher không hợp lệ.'))
        if card.expiration_date and card.expiration_date < fields.Date.today():
            raise UserError(_('Mã voucher đã hết hạn.'))
        reward = card.program_id.reward_ids[:1]
        if not reward or card.points < reward.required_points:
            raise UserError(_('Mã voucher đã được sử dụng hoặc không còn khả dụng.'))
        if reward.discount_applicability == 'specific':
            # CỐ TÌNH không dùng reward.all_discount_product_ids - field tính sẵn này bị
            # khóa rỗng toàn cục khi tham số hệ thống loyalty.compute_all_discount_product_ids
            # = False (Odoo tự tắt để tối ưu hiệu năng lúc catalog lớn), gây báo sai "không
            # áp dụng" dù cấu hình đúng - đã kiểm chứng thực tế trên DB. Tự dò lại đúng domain
            # qua _get_discount_product_domain() (đúng logic Odoo dùng nội bộ), không phụ
            # thuộc tham số bật/tắt đó.
            product = course_record.product_id.product_variant_id if course_record else False
            domain = reward._get_discount_product_domain()
            if not product or not self.env['product.product'].sudo().search_count(
                    domain + [('id', '=', product.id)]):
                raise UserError(_('Mã voucher không áp dụng cho khóa học này.'))
        if reward.discount_mode == 'percent':
            discount = amount * (reward.discount / 100)
        elif reward.discount_mode == 'per_order':
            discount = min(amount, reward.discount)
        else:
            raise UserError(_('Loại phiếu giảm giá này chưa được hỗ trợ.'))
        return card, round(discount), round(amount - discount)

    # Dùng CHUNG cho 3 diện cần nộp giấy tờ (education_scholarship/medical_scholarship/
    # nonprofit) - Many2many ir.attachment, đúng widget many2many_binary chuẩn Odoo cho
    # nhiều file, không cần model riêng cho từng diện.
    category_attachment_ids = fields.Many2many(
        'ir.attachment', string='Giấy tờ/tài liệu đính kèm',
    )

    # --- Diện học bổng ngành y / Diện tổ chức phi lợi nhuận ---
    # Field theo diện y tế/tổ chức KHÔNG khai riêng từng field như voucher/học phí ở
    # trên - dùng model con dạng label/value CHUNG (seroto.course.registration.
    # category_info), hiển thị dạng list editable="bottom" y hệt answer_ids/"Câu hỏi
    # chuyên sâu" bên dưới (nhân viên yêu cầu đúng UI này). Controller
    # (create_registration) tự ghép label cố định theo từng diện lúc tạo phiếu.
    category_info_ids = fields.One2many(
        'seroto.course.registration.category.info', 'registration_id',
        string='Thông tin theo diện đăng ký',
    )

    answer_ids = fields.One2many(
        'seroto.course.registration.answer', 'registration_id',
        string='Câu trả lời (Thông tin chuyên sâu)',
    )
    # Trả lời NGAY Ở BƯỚC 1 "Thông tin cơ bản" - ghi 1 LẦN lúc tạo/cập nhật phiếu (khác
    # answer_ids ở trên, có thể ghi lại nhiều lần sau khi phiếu đã tồn tại).
    basic_answer_ids = fields.One2many(
        'seroto.course.registration.basic.answer', 'registration_id',
        string='Câu trả lời (Thông tin cơ bản)',
    )
    payment_status = fields.Selection(
        [('unpaid', 'Chưa thanh toán'), ('paid', 'Đã thanh toán')],
        string='Trạng thái thanh toán', default='unpaid', required=True,
    )

    state = fields.Selection([
        ('draft', 'Nháp'),
        ('new', 'Mới đăng ký'),
        ('confirmed', 'Đã xác nhận'),
        ('completed', 'Hoàn tất'),
        ('rejected', 'Đã từ chối'),
        ('cancelled', 'Đã hủy'),
    ], string='Trạng thái', default='draft', required=True, tracking=True)
    reject_reason = fields.Text(string='Lý do từ chối')
    sale_order_id = fields.Many2one('sale.order', string='Đơn hàng', readonly=True, copy=False)
    # Phiếu thu (account.payment) do hệ thống TỰ TẠO ngay khi payOS báo đã nhận tiền -
    # xem _auto_process_payment(). Đây là chứng từ kế toán thật (khác
    # payos_transaction_id ở dưới chỉ là log kỹ thuật của cổng thanh toán) - giữ lại để
    # tiện tra cứu ngược từ phiếu đăng ký ra thẳng sổ sách.
    payment_id = fields.Many2one('account.payment', string='Phiếu thu', readonly=True, copy=False)

    is_complete = fields.Boolean(
        string='Đã đầy đủ thông tin', compute='_compute_is_complete', store=True,
        help='Đã có Khóa học/Lớp học liên kết và đã trả lời hết các câu hỏi chuyên sâu hiện tại của khóa học.',
    )

    # Học phí GỐC của Khóa học liên kết (product_id.list_price) - CỐ TÌNH không tính
    # giảm giá/voucher vào đây (khác hẳn _get_payment_amount()) - dùng để nhân viên đối
    # chiếu mức giá chuẩn của khóa, không lẫn với số tiền THẬT cần thu (xem
    # "Số tiền cần thanh toán" ở pane Thanh toán phía website, cũng tách riêng 2 số này).
    expected_amount = fields.Monetary(
        string='Học phí tương ứng theo khóa học', compute='_compute_expected_amount',
    )

    @api.depends('course_id.product_id.list_price')
    def _compute_expected_amount(self):
        for rec in self:
            rec.expected_amount = rec._get_base_amount()

    def _get_base_amount(self):
        """Học phí GỐC theo Khóa học liên kết - CHƯA áp bất kỳ giảm giá/voucher nào (so
        sánh với _get_payment_amount() bên dưới, số tiền THẬT cần thu sau khi đã áp).
        """
        self.ensure_one()
        if self.course_id and self.course_id.product_id:
            return self.course_id.product_id.list_price
        return 0

    @api.onchange('course_id', 'registration_category')
    def _onchange_course_id_questions(self):
        """Đồng bộ lại answer_ids theo đúng bộ Câu hỏi chuyên sâu ÁP DỤNG cho Khóa học +
        Diện đăng ký hiện tại (is_shared hoặc khớp registration_category, xem
        _get_course_questions()) - dành cho luồng NV tạo/sửa phiếu tay trên backend
        (chọn course_id qua Many2one, hoặc đổi Diện đăng ký). Luồng web không đi qua đây
        - JS tự quản lý câu hỏi/câu trả lời riêng ở client, ghi thẳng answer_ids qua ORM
        create()/write() (xem controllers/course_registration.py) - route đó không qua
        onchange nên không bị ảnh hưởng; phiếu tạo qua web đã tự pre-seed answer_ids
        rỗng ngay lúc create() (xem create() bên dưới), NV vẫn thấy đủ câu hỏi cần hỏi
        trên backend dù khách CHƯA trả lời câu nào.

        Giữ lại câu trả lời cũ nếu câu hỏi đó (so trùng nội dung) vẫn còn trong bộ câu
        hỏi mới - chỉ thêm dòng cho câu hỏi chưa có, bỏ dòng cho câu hỏi không còn thuộc
        khóa học/diện hiện tại (trước đây đổi Khóa học không làm gì cả, tab Câu hỏi
        chuyên sâu cứ giữ nguyên/trống, không khớp khóa học thật đang chọn).
        """
        for rec in self:
            questions = (
                [q['question'] for q in rec._get_course_questions(rec.course_id.name)]
                if rec.course_id else []
            )
            existing = {a.question: a.answer for a in rec.answer_ids}
            rec.answer_ids = [(5, 0, 0)] + [
                (0, 0, {'question': q, 'answer': existing.get(q, '')})
                for q in questions
            ]

    @api.onchange('registration_category')
    def _onchange_registration_category_info(self):
        """Tự dựng lại đúng bộ nhãn category_info_ids theo diện MỚI chọn - dành cho lúc
        NHÂN VIÊN tự đổi "Diện đăng ký" trên backend (registration_category cho sửa tự
        do, không khoá theo state - xem views/course_registration_views.xml). Phiếu tạo
        qua website đã có sẵn category_info_ids đúng diện lúc đăng ký (xem controllers/
        course_registration.py, create_registration) - hàm này CHỈ chạy khi có thao tác
        đổi field trên form, không ảnh hưởng luồng tạo phiếu qua web.

        Giữ lại value cũ nếu nhãn đó (so trùng nội dung) vẫn còn trong bộ nhãn mới -
        lỡ đổi qua diện khác rồi đổi lại không mất dữ liệu đã điền, đúng tinh thần
        _onchange_course_id_questions ở trên.
        """
        for rec in self:
            labels = CATEGORY_INFO_LABELS.get(rec.registration_category, [])
            existing = {info.label: info.value for info in rec.category_info_ids}
            rec.category_info_ids = [(5, 0, 0)] + [
                (0, 0, {'label': label, 'value': existing.get(label, '')})
                for label in labels
            ]

    @api.onchange('registration_category', 'course_id')
    def _onchange_registration_category_pricing(self):
        """Tự nạp mặc định early_price/discount_percent theo đúng cấu hình của Khóa
        học (academic.course.pricing_ids, 1 dòng/diện - module seroto_education) mỗi
        khi đổi Diện đăng ký hoặc Khóa học - nhân viên vẫn sửa tay lại được sau đó, y
        hệt tinh thần _onchange_registration_category_info ở trên. Mỗi dòng cấu hình đã
        tự gắn với ĐÚNG 1 diện (course_id + registration_category), nên 2 diện học bổng
        khác nhau vẫn có mức giảm riêng dù đọc chung field discount_percent của dòng đó.
        """
        for rec in self:
            pricing = rec.course_id.pricing_ids.filtered(
                lambda p: p.registration_category == rec.registration_category
            )
            if rec.registration_category == 'tuition':
                rec.early_price = pricing.early_price
            elif rec.registration_category in (
                    'education_scholarship', 'medical_scholarship', 'nonprofit'):
                rec.discount_percent = pricing.discount_percent

    @api.depends('course_id.question_ids.question', 'course_id.question_ids.is_shared',
                 'course_id.question_ids.registration_category_ids', 'registration_category',
                 'answer_ids.question', 'answer_ids.answer', 'partner_name', 'email', 'phone')
    def _compute_is_complete(self):
        for rec in self:
            if not (rec.partner_name and rec.email and rec.phone):
                rec.is_complete = False
                continue
            # CHỈ xét câu hỏi ÁP DỤNG cho đúng Diện đăng ký hiện tại (is_shared/khớp
            # category) - trước đây bắt trả lời CẢ câu hỏi của diện khác, is_complete
            # không bao giờ = True dù khách đã trả lời đủ câu hỏi thật sự liên quan.
            required_questions = [
                q['question'] for q in rec._get_course_questions(rec.course_id.name)
            ] if rec.course_id else []
            answered = {a.question for a in rec.answer_ids if (a.answer or '').strip()}
            rec.is_complete = all(q in answered for q in required_questions)

    # Cho phép khách xem/tiếp tục phiếu qua link trong email mà KHÔNG cần đăng nhập -
    # so khớp token thay vì id để không ai đoán được link phiếu của người khác.
    access_token = fields.Char(
        string='Mã truy cập phiếu', required=True, copy=False, readonly=True,
        default=lambda self: secrets.token_urlsafe(24),
    )

    # Giao dịch thanh toán payOS (module vtt_payos - xem _create_payment_transaction())
    # tương ứng với phiếu này. GIỮ LẠI để tương thích ngược (dữ liệu cũ, các chỗ khác
    # trong code đang đọc field này) - không hiển thị trực tiếp trên form nữa, xem
    # payment_transaction_ref bên dưới.
    payos_transaction_id = fields.Many2one(
        'payos.transaction', string='Giao dịch payOS', copy=False,
    )

    # Field TỔNG QUÁT thay cho việc hiển thị thẳng payos_transaction_id trên form - trỏ
    # tới ĐÚNG bản ghi giao dịch đã dùng, không cố định phải là payOS. Cố tình liệt kê
    # sẵn cả 'bank.mock.transaction' (module vtt_bank_mock/vtt_payment_dev_switch, CHỈ
    # dev mới cài) dù vtt_seroto_website không phụ thuộc module đó - Reference field chỉ
    # cần tên model đúng lúc THỰC SỰ có bản ghi trỏ tới, không bắt buộc module phải cài
    # sẵn chỉ vì có mặt trong danh sách lựa chọn. Thêm cổng thanh toán thật mới sau này
    # (VD MoMo, VNPay) chỉ cần thêm 1 dòng vào selection này.
    payment_transaction_ref = fields.Reference(
        selection=[
            ('payos.transaction', 'PayOS'),
            ('bank.mock.transaction', 'Giả lập (dev)'),
        ],
        string='Giao dịch', copy=False,
    )
    # Tên cổng dạng chữ ("PayOS"/"Giả lập (dev)") lấy lại TỪ selection của
    # payment_transaction_ref (không lặp lại chuỗi lần 2) - tránh phải bấm vào Giao
    # dịch mới biết đang dùng cổng nào.
    payment_provider_label = fields.Char(
        string='Cổng thanh toán', compute='_compute_payment_provider_label',
    )

    @api.depends('payment_transaction_ref')
    def _compute_payment_provider_label(self):
        provider_names = dict(self._fields['payment_transaction_ref'].selection)
        for rec in self:
            rec.payment_provider_label = (
                provider_names.get(rec.payment_transaction_ref._name)
                if rec.payment_transaction_ref else False
            )

    # Đúng link đã gửi trong email xác nhận (_send_confirmation_email) - hiện trên form
    # backend để nhân viên copy gửi lại thủ công (Zalo/điện thoại...) khi khách cần,
    # không phải tìm lại trong email cũ.
    slip_url = fields.Char(string='Link phiếu đăng ký', compute='_compute_slip_url')

    @api.depends('access_token')
    def _compute_slip_url(self):
        for rec in self:
            rec.slip_url = rec._get_slip_url() if rec.id else False

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '[%s]' % rec.code if rec.code else _('Phiếu đăng ký mới')

    def _get_slip_url(self):
        self.ensure_one()
        return '%s/dang-ky-khoa-hoc/phieu/%s/%s' % (self.get_base_url(), self.id, self.access_token)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('course_name') and not vals.get('course_id'):
                course = self.env['academic.course'].sudo().search(
                    [('name', '=', vals['course_name'])], limit=1,
                )
                if course:
                    vals['course_id'] = course.id
                    if not vals.get('class_id'):
                        vals['class_id'] = course.default_class_id.id
        records = super().create(vals_list)
        # Gán "code" (Mã phiếu) SAU khi tạo - cần có id thật để ghép chuỗi, không đưa
        # được vào vals lúc create() như các field khác.
        for rec in records:
            rec.code = 'PDK%s' % rec.id
            # Pre-seed answer_ids RỖNG cho MỌI câu hỏi áp dụng NGAY lúc tạo phiếu -
            # trước đây answer_ids HOÀN TOÀN RỖNG tới khi khách tự trả lời, NV mở phiếu
            # trên backend không biết cần hỏi khách những gì. "not rec.answer_ids" tránh
            # ghi đè answer_ids nếu vals đã có sẵn (VD luồng backend qua onchange đã tự
            # dựng từ trước).
            if rec.course_id and not rec.answer_ids:
                rec._sync_answer_ids()
        return records

    def _sync_answer_ids(self):
        """Đồng bộ answer_ids theo ĐÚNG bộ câu hỏi áp dụng hiện tại (is_shared/khớp
        diện, xem _get_course_questions()) - thêm dòng RỖNG cho câu hỏi mới (VD NV vừa
        thêm câu hỏi vào Khóa học sau khi phiếu đã tạo), và XÓA dòng RỖNG (answer chưa
        điền) có câu hỏi KHÔNG CÒN khớp bộ câu hỏi hiện tại (VD NV vừa đổi tên câu hỏi
        trên Khóa học - dòng rỗng theo tên CŨ giờ chỉ còn là rác, không ai trả lời được
        nữa vì tên mới mới là cái đang hỏi khách).

        Dòng ĐÃ có trả lời thật (answer khác rỗng) KHÔNG BAO GIỜ bị đụng tới dù tên câu
        hỏi không còn khớp nữa - giữ nguyên lịch sử đúng câu đã hỏi khách lúc đó (xem
        comment trên SerotoCourseRegistrationAnswer.question).

        Gọi ở các điểm khách/NV thực sự XEM lại phiếu (view_registration_slip,
        _build_registration_response, xem controllers/course_registration.py) để tự dọn
        rác mà không cần chờ NV mở đúng form backend rồi tự tay đổi field mới kích hoạt
        được _onchange_course_id_questions (vốn cũng làm việc này, nhưng CHỈ chạy khi có
        thao tác trên UI backend).
        """
        for rec in self:
            if not rec.course_id:
                continue
            questions = [q['question'] for q in rec._get_course_questions(rec.course_id.name)]
            existing_questions = set(rec.answer_ids.mapped('question'))
            stale = rec.answer_ids.filtered(
                lambda a: not (a.answer or '').strip() and a.question not in questions
            )
            stale.unlink()
            missing = [q for q in questions if q not in existing_questions]
            if missing:
                self.env['seroto.course.registration.answer'].create([
                    {'registration_id': rec.id, 'question': q, 'answer': ''}
                    for q in missing
                ])

    def action_confirm(self):
        """Gộp luôn bước Tạo đơn hàng vào đây (trước đây phải bấm 2 nút riêng: Xác nhận
        rồi mới tới Tạo đơn hàng) - Sale bấm 1 lần là xong, mở thẳng qua Đơn hàng vừa
        tạo để kiểm tra/xác nhận tiếp. Nút "Tạo đơn hàng" trên form vẫn giữ lại - không
        còn xuất hiện trong luồng bình thường (sale_order_id đã có sẵn ngay khi state
        chuyển "confirmed"), chỉ còn là lối khắc phục nếu luồng tự động
        (_auto_process_payment) lỡ set state="confirmed" nhưng lỗi giữa chừng trước khi
        tạo được Đơn hàng.
        """
        self.ensure_one()
        self.write({'state': 'confirmed'})
        order = self._create_sale_order()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': order.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _requires_category_confirmation(self):
        """3 diện cần nộp giấy tờ/thông tin (education_scholarship/medical_scholarship/
        nonprofit) - PHẢI đợi nhân viên bấm "Xác nhận thông tin đăng ký"
        (action_confirm_category_discount) mới có link/QR thanh toán (xem
        controllers/course_registration.py, create_registration/update_basic_registration)
        - tránh khách thanh toán ngay giá GỐC (chưa áp mức giảm) trước khi nhân viên kịp
        duyệt giấy tờ.
        """
        self.ensure_one()
        return self.registration_category in (
            'education_scholarship', 'medical_scholarship', 'nonprofit')

    def action_confirm_category_discount(self):
        """Nút "Xác nhận thông tin đăng ký" - CHỈ dành cho 3 diện cần nộp giấy tờ
        (education_scholarship/medical_scholarship/nonprofit, xem invisible trên view).
        Nhân viên bấm sau khi đã tự kiểm tra giấy tờ/thông tin đính kèm (category_
        attachment_ids/category_info_ids) hợp lệ - KHÔNG tự động validate nội dung giấy
        tờ (không có gì để máy kiểm tra được), chỉ ghi nhận xác nhận của con người, y hệt
        tinh thần popup confirm hỏi lại trước khi thực hiện (xem confirm= trên view).

        Áp dụng ĐÚNG mức giảm đã cấu hình (discount_percent, tự nạp theo Khóa học qua
        _onchange_registration_category_pricing, nhân viên có thể đã sửa tay) bằng cách
        tạo lại giao dịch thanh toán (_create_payment_transaction, tự đọc lại amount mới
        qua _get_payment_amount) - khách vào lại ĐÚNG link phiếu cũ trong email sẽ tự
        thấy QR/số tiền mới, không cần gửi lại email (checkout_url/qr_url luôn đọc TRỰC
        TIẾP từ payment_transaction_ref hiện tại, không cache).

        Giảm đủ 100% (amount = 0) thì bỏ qua hẳn bước thanh toán - tự động đánh dấu Đã
        thanh toán và chạy tiếp luồng tự động y hệt lúc payOS báo đã nhận tiền
        (_auto_process_payment) - đúng quyết định đã chốt cùng người dùng trước đây.
        """
        self.ensure_one()
        if not self._requires_category_confirmation():
            raise UserError(
                _('Chỉ áp dụng cho Diện học bổng giáo dục/học bổng ngành y/tổ chức phi lợi nhuận.')
            )
        self.category_discount_confirmed = True
        amount = self._get_payment_amount()
        # Ghi log vào chatter - NV bấm nút này là 1 quyết định nghiệp vụ quan trọng
        # (xác nhận giấy tờ hợp lệ + chốt mức giảm), khác hẳn các thay đổi field thông
        # thường (đã tự có tracking qua state), cần thấy rõ AI đã xác nhận, LÚC NÀO,
        # và mức giảm/số tiền cuối cùng là bao nhiêu để đối chiếu sau này.
        self.message_post(
            body=Markup(
                '<p>%s</p>'
                '<ul>'
                '<li>%s <b>%s%%</b></li>'
                '<li>%s <b>%sđ</b></li>'
                '</ul>'
            ) % (
                _('Đã xác nhận thông tin/giấy tờ đăng ký hợp lệ'),
                _('Áp dụng mức giảm học phí:'),
                self.discount_percent,
                _('Số tiền cần thanh toán:'),
                '{:,.0f}'.format(amount).replace(',', '.'),
            )
        )
        if amount <= 0:
            if self.payment_status != 'paid':
                self.payment_status = 'paid'
            self._auto_process_payment()
        else:
            self._create_payment_transaction()

    def action_reject(self):
        self.ensure_one()
        return {
            'name': 'Từ chối phiếu đăng ký',
            'type': 'ir.actions.act_window',
            'res_model': 'seroto.course.registration.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_registration_id': self.id},
        }

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def _find_or_create_partner(self):
        self.ensure_one()
        if self.partner_id:
            return self.partner_id

        Partner = self.env['res.partner'].sudo()
        domain = [('is_company', '=', False)]
        if self.email:
            domain += ['|', ('email', '=', self.email), ('phone', '=', self.phone)]
        else:
            domain += [('phone', '=', self.phone)]
        partner = Partner.search(domain, limit=1)

        if not partner:
            partner = Partner.create({
                'name': self.partner_name,
                'email': self.email,
                'phone': self.phone,
            })
        self.partner_id = partner.id
        return partner

    def _find_or_create_student_partner(self, registrant):
        """Học viên thực tế - trùng với người đăng ký (registrant) nếu student_relation
        = "self". Khác thì tìm/tạo 1 liên hệ riêng, gắn parent_id = registrant để khớp
        đúng domain của sale.order.line.student_id (xem seroto_education/models/
        sale_order.py) - CHỈ cho chọn chính registrant hoặc con/liên hệ của registrant.
        """
        self.ensure_one()
        if self.student_relation == 'self' or not (self.student_name or '').strip():
            return registrant

        Partner = self.env['res.partner'].sudo()
        student = Partner.search([
            ('name', '=', self.student_name.strip()),
            ('parent_id', '=', registrant.id),
        ], limit=1)
        if not student:
            student = Partner.create({
                'name': self.student_name.strip(),
                'parent_id': registrant.id,
                'is_company': False,
            })
        return student

    def _create_sale_order(self):
        """Tạo Đơn hàng (Nháp) cho phiếu này - tách riêng khỏi action_create_sale_order()
        để dùng chung được cho cả nút bấm tay (Sale) lẫn luồng tự động
        (_auto_process_payment, xem dưới)."""
        self.ensure_one()
        registrant = self._find_or_create_partner()
        student = self._find_or_create_student_partner(registrant)

        order_line_vals = []
        if self.course_id.product_id:
            line_vals = {
                'product_id': self.course_id.product_id.id,
                'class_id': self.class_id.id if self.class_id else False,
                'student_id': student.id,
            }
            # Áp cùng logic giá của _get_payment_amount() lên dòng Đơn hàng thật - dùng
            # ĐÚNG field "discount" (%) có sẵn của sale.order.line cho 3 diện giảm giá
            # (để Odoo tự tính tiền, không tự làm tay), ghi đè thẳng price_unit cho
            # tuition đăng ký sớm. Nhánh voucher KHÔNG cần gì thêm ở đây - _try_apply_code
            # bên dưới tự lo phần chiết khấu trên Đơn hàng.
            if self.registration_category == 'tuition' and self.early_registration_status == 'early' and self.early_price:
                line_vals['price_unit'] = self.early_price
            elif self.registration_category in ('education_scholarship', 'medical_scholarship', 'nonprofit') and self.discount_percent:
                line_vals['discount'] = self.discount_percent
            order_line_vals.append((0, 0, line_vals))

        order = self.env['sale.order'].sudo().create({
            'partner_id': registrant.id,
            'order_line': order_line_vals,
        })
        self.sale_order_id = order.id

        # Diện voucher - áp mã "Phiếu giảm giá" NGAY TRÊN Đơn hàng bằng ĐÚNG luồng chuẩn
        # của Odoo (sale_loyalty._try_apply_code, module loyalty đã khai depends) thay vì
        # tự trừ points tay - Odoo tự lo đúng phần tạo dòng chiết khấu trên đơn, ghi
        # loyalty.history, trừ points, thay vì code ở đây tự làm lệch với cách Odoo ghi
        # nhận. Mã đã validate hợp lệ lúc tạo phiếu (_validate_voucher_code, xem
        # controllers/course_registration.py) chỉ để TÍNH học phí cho link thanh toán,
        # KHÔNG trừ points ở đó - điểm chỉ thực sự bị tiêu ở đây, đúng lúc Đơn hàng thật
        # được tạo. 'error' (VD mã đã bị người khác dùng hết trong lúc chờ thanh toán) chỉ
        # log lại - không chặn cả luồng tạo Đơn hàng, Sale tự xử lý chênh lệch giá nếu có.
        if self.registration_category == 'voucher' and self.voucher_code:
            result = order._try_apply_code(self.voucher_code)
            if isinstance(result, dict) and result.get('error'):
                _logger.warning(
                    'Không áp được mã voucher "%s" lên Đơn hàng %s (phiếu ID=%s): %s',
                    self.voucher_code, order.name, self.id, result.get('error'),
                )

        return order

    def action_create_sale_order(self):
        self.ensure_one()
        order = self._create_sale_order()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': order.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _auto_process_payment(self):
        """Tự động Tạo đơn hàng -> Xác nhận -> Tạo hóa đơn -> Đăng sổ -> Đăng ký thanh
        toán ngay khi payOS báo đã nhận tiền (_payos_on_paid gọi hàm này sau khi ghi
        payment_status='paid') - thay cho việc Sale phải tự bấm từng bước như trước.
        Ghi danh học viên tự phát sinh theo sau, không cần code thêm ở đây - đã
        có sẵn hook _sync_enrollments_on_payment (seroto_education/models/account_move.py)
        kích hoạt mỗi khi payment_state của hóa đơn chuyển "paid"/"in_payment".

        Việc trả lời Câu hỏi chuyên sâu (answer_ids) KHÔNG phải điều kiện cho luồng này -
        is_complete chỉ mang tính hiển thị/lọc ("Cần xử lý"), khách có thể điền trước
        hoặc sau khi đã được ghi danh.

        Chống webhook gọi lặp (ngân hàng/cổng thanh toán hay tự động thử lại): bỏ qua
        toàn bộ nếu đã có sale_order_id - nghĩa là lần gọi trước đã xử lý (hoặc đang xử
        lý) phiếu này rồi, không tạo trùng Đơn hàng/Hóa đơn/Phiếu thu.

        Lỗi ở bất kỳ bước nào chỉ log lại, KHÔNG được làm mất payment_status='paid' đã
        lưu trước khi gọi hàm này - Sale vẫn thấy đúng phiếu đã thanh toán để xử lý tay
        phần còn lại, y hệt luồng thủ công trước khi có tự động hóa này.
        """
        self.ensure_one()
        if self.sale_order_id:
            return

        try:
            self.state = 'confirmed'
            order = self._create_sale_order()
            order.sudo().action_confirm()

            invoices = order.sudo()._create_invoices()
            invoices.sudo().action_post()

            for invoice in invoices:
                register = self.env['account.payment.register'].sudo().with_context(
                    active_model='account.move', active_ids=invoice.ids,
                ).create({
                    # Nối ngược lại đúng phiếu đăng ký + giao dịch payOS đã kích hoạt
                    # bước này - phục vụ đối soát/tra cứu sau này (xem payment_id,
                    # payos_transaction_id ở trên).
                    'communication': 'PDK%s (payOS %s)' % (self.id, self.payos_transaction_id.order_code),
                })
                payments = register._create_payments()
                if payments:
                    self.payment_id = payments[0].id
        except Exception:
            _logger.exception(
                'Không tự xử lý được Đơn hàng/Hóa đơn/Thanh toán cho phiếu đăng ký '
                'ID=%s - phiếu đã ghi nhận payment_status=paid, cần Sale kiểm tra và '
                'xử lý tay phần còn lại.', self.id,
            )

    def _payos_on_paid(self, transaction):
        """Quy ước payos.transaction gọi tới (xem vtt_payos/models/payos_transaction.py,
        _notify_related_record) ngay khi giao dịch chuyển "Đã thanh toán" - dù đến từ
        webhook payOS gọi về hay từ cron đối soát định kỳ. Thay thế đúng vị trí trước
        đây do bank_notify_webhook (controllers/course_registration.py) đảm nhiệm.
        """
        self.ensure_one()
        if self.payment_status != 'paid':
            self.payment_status = 'paid'
        self._auto_process_payment()

    def action_view_sale_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _get_course_questions(self, course_name):
        """Bộ câu hỏi "Thông tin chuyên sâu" của khóa học (tab "Câu hỏi chuyên sâu" trên
        form academic.course, module seroto_education) - khớp theo TÊN khóa học (giống
        cách course_name được truyền vào từ đầu, xem s_trang_chu_course.xml), không có
        khóa học khớp tên hoặc chưa cấu hình câu hỏi nào thì trả về rỗng (Tab 3 của
        wizard khi đó chỉ còn bước "Hoàn tất", không có câu nào để điền).

        CỐ TÌNH tra bằng self.env['academic.course'] thay vì khai báo phụ thuộc cứng
        vào seroto_education trong __manifest__.py - giống cách course_snippet.js/
        s_course_card.xml trong module này đã tra 'seroto.course' (module seroto_form)
        từ trước, không phải quyết định mới.

        Chỉ lấy câu hỏi "Dùng chung" (is_shared) hoặc khớp ĐÚNG 1 trong các diện đã chọn
        cho câu hỏi đó (registration_category_ids, Many2many - 1 câu hỏi áp dụng được
        cho NHIỀU diện cùng lúc, so khớp bằng "code" chứ không phải id - xem
        academic.registration.category, module seroto_education) của self (self luôn
        là 1 bản ghi phiếu đăng ký thật ở cả 2 nơi gọi hàm này -
        _build_registration_response/view_registration_slip, xem controllers/
        course_registration.py) - câu hỏi cũ (chưa từng cấu hình diện) mặc định
        is_shared=True nên vẫn hiển thị bình thường ở mọi diện, không bị mất.
        """
        Course = self.env['academic.course'].sudo()
        course = Course.search([('name', '=', course_name)], limit=1)
        if not course:
            return []
        category = self.registration_category if len(self) == 1 else False
        questions = course.question_ids.filtered(
            lambda q: q.is_shared or category in q.registration_category_ids.mapped('code')
        )
        return [
            {
                'id': question.id,
                'question': question.question,
                'question_type': question.question_type,
                # Mỗi lựa chọn 1 dòng trên form Khóa học -> tách thành mảng cho JS dựng
                # dropdown/nhóm ô chọn (xem question_ids trên academic.course.question -
                # KHÔNG dùng dấu phẩy để tránh đụng lựa chọn tự nó chứa dấu phẩy).
                'options': [
                    line.strip() for line in (question.options or '').split('\n') if line.strip()
                ],
            }
            for question in questions
        ]

    @api.model
    def _get_basic_questions_raw(self, course_name):
        """Toàn bộ Câu hỏi cơ bản (academic.course.basic.question, module seroto_education)
        của khóa học - KHÔNG lọc theo diện (khác _get_course_questions() ở trên, nơi ĐÃ
        biết registration_category của 1 Phiếu đăng ký thật). Câu hỏi cơ bản hiện Ở BƯỚC 1
        "Thông tin cơ bản", TRƯỚC KHI Phiếu đăng ký tồn tại, nên gọi được ngay lúc mở modal
        (xem controllers/academic_course_snippet.py, academic_course_is_registration_open)
        - JS tự lọc lại theo diện đang chọn mỗi khi đổi dropdown (course_register_wizard.js,
        _renderBasicQuestions/_onCategoryChange), kèm is_shared/category_codes để lọc.
        """
        Course = self.env['academic.course'].sudo()
        course = Course.search([('name', '=', course_name)], limit=1)
        if not course:
            return []
        return [
            {
                'id': question.id,
                'question': question.question,
                'question_type': question.question_type,
                'options': [
                    line.strip() for line in (question.options or '').split('\n') if line.strip()
                ],
                'is_shared': question.is_shared,
                'category_codes': question.registration_category_ids.mapped('code'),
            }
            for question in course.basic_question_ids
        ]

    @api.model
    def _get_applicable_basic_questions(self, course_name, registration_category):
        """Câu hỏi cơ bản ÁP DỤNG cho ĐÚNG 1 diện cụ thể - dùng để validate THẬT ở server
        (controllers/course_registration.py, _prepare_registration_vals) rằng khách đã
        trả lời đủ, không chỉ dựa vào JS.
        """
        return [
            q for q in self._get_basic_questions_raw(course_name)
            if q['is_shared'] or registration_category in q['category_codes']
        ]

    def _get_payment_amount(self):
        """Số tiền THẬT cần thu cho phiếu này - dùng CHUNG cho MỌI cổng thanh toán (payOS
        thật lẫn giả lập dev, xem vtt_payment_dev_switch/models/course_registration.py
        _create_dev_bank_mock_transaction()). CỐ TÌNH tách riêng thành 1 method duy nhất -
        trước đây nhánh giả lập tự tính lại `amount` riêng, bỏ sót hoàn toàn phần giảm giá
        voucher (đã xảy ra thực tế) vì 2 nơi tính theo 2 cách khác nhau.
        """
        self.ensure_one()
        # Lấy đúng giá GỐC (chưa giảm) của Sản phẩm liên kết - course_id đã tự suy ra từ
        # course_name lúc create() (nếu khớp được tên khóa học). Không khớp được khóa
        # học hoặc khóa học chưa gắn sản phẩm thì để 0đ (thà rõ ràng là chưa xác định
        # được giá còn hơn hiện nhầm số của phiếu khác).
        amount = self._get_base_amount()
        # Diện đóng học phí + đã chọn "Đăng ký sớm" - dùng thẳng early_price (mặc định
        # nạp từ Khóa học, nhân viên có thể đã sửa riêng cho phiếu này, xem
        # _onchange_registration_category_pricing).
        if self.registration_category == 'tuition' and self.early_registration_status == 'early' and self.early_price:
            amount = self.early_price
        # 3 diện học bổng/phi lợi nhuận - giảm theo % (discount_percent, cùng quy ước
        # 0-100 như field discount có sẵn của sale.order.line, xem _create_sale_order).
        elif self.registration_category in ('education_scholarship', 'medical_scholarship', 'nonprofit') and self.discount_percent:
            amount = amount * (1 - self.discount_percent / 100)
        # Diện voucher đã có mã hợp lệ - dùng ĐÚNG số tiền đã tính sẵn lúc tạo phiếu
        # (_validate_voucher_code, gọi từ controller), không tính lại ở đây để tránh sai
        # lệch làm tròn giữa 2 lần tính.
        elif self.registration_category == 'voucher' and self.loyalty_card_id:
            amount = self.voucher_final_amount
        return amount

    def _create_payment_transaction(self):
        """Tạo link thanh toán payOS thật cho phiếu này - khách quét QR hoặc mở
        checkout_url để thanh toán. payOS gọi thẳng về payos_transaction._process_paid()
        (qua webhook cố định /payos/webhook, module vtt_payos) rồi tự tìm tới
        _payos_on_paid() ở trên theo đúng quy ước related_res_model/related_res_id.
        """
        self.ensure_one()
        amount = self._get_payment_amount()
        slip_url = self._get_slip_url()
        transaction = self.env['payos.transaction'].sudo().create_for_record(
            amount=round(amount),
            # payOS giới hạn nội dung chuyển khoản ngắn (không dấu, không quá ~25 ký
            # tự) - dùng đúng Mã phiếu (self.code, khớp _compute_display_name) để dễ đối
            # chiếu ngược từ nội dung chuyển khoản thật ra đúng phiếu, không nhét thêm
            # tên khóa học/sđt như bản giả lập trước đây vì dễ vượt giới hạn của payOS.
            description=self.code,
            related_record=self,
            return_url=slip_url,
            cancel_url=slip_url,
        )
        self.payos_transaction_id = transaction.id
        self.payment_transaction_ref = 'payos.transaction,%s' % transaction.id
        return transaction

    def _get_checkout_url(self):
        self.ensure_one()
        return self.payos_transaction_id.checkout_url if self.payos_transaction_id else False

    def _get_checkout_qr_url(self):
        self.ensure_one()
        return self.payos_transaction_id._get_qr_image_url() if self.payos_transaction_id else False

    def action_send_confirmation_email(self):
        for registration in self:
            registration._send_confirmation_email()

    def _send_confirmation_email(self):
        self.ensure_one()

        body_html = self.env['ir.qweb']._render(
            'vtt_seroto_website.course_registration_email',
            {'registration': self, 'slip_url': self._get_slip_url()},
        )

        # email_from PHẢI truyền tay - request này chạy dưới "Public User" (khách web
        # chưa đăng nhập), không có email riêng để Odoo tự suy ra người gửi (chỉ tự suy
        # ra được khi env.user có email, vd tài khoản nội bộ) - thiếu dòng này Odoo báo
        # lỗi "mail_from_missing" dù đã cấu hình Outgoing Mail Server đầy đủ (đã gặp
        # thực tế). company.email khớp với tài khoản SMTP đang cấu hình.
        # formataddr bọc thành '"Tên" <email>' - nếu chỉ truyền chuỗi email trần, mail
        # client (Gmail...) không có tên để hiển thị, chỉ show mỗi địa chỉ.
        company = self.env.company
        email_from = formataddr((company.name, company.email or self.env.user.email))

        # Không để lỗi gửi mail (vd chưa cấu hình Outgoing Mail Server) làm hỏng cả
        # luồng đăng ký - phiếu vẫn được tạo, chỉ log lại để kiểm tra sau.
        try:
            self.env['mail.mail'].sudo().create({
                'subject': 'Xác nhận đăng ký khóa học "%s" - Seroto' % self.course_name,
                'email_to': self.email,
                'email_from': email_from,
                'body_html': body_html,
            }).send()
        except Exception:
            _logger.exception(
                'Không gửi được email xác nhận đăng ký khóa học cho phiếu ID=%s', self.id
            )


class SerotoCourseRegistrationAnswer(models.Model):
    _name = 'seroto.course.registration.answer'
    _description = 'Trả lời câu hỏi chuyên sâu (Phiếu đăng ký khóa học)'
    _order = 'id'

    registration_id = fields.Many2one(
        'seroto.course.registration', string='Phiếu đăng ký', required=True, ondelete='cascade',
    )
    # Lưu lại TEXT câu hỏi ngay lúc đăng ký (không Many2one sang academic.course.question)
    # - dù sau này khóa học đổi/xóa câu hỏi, phiếu cũ vẫn giữ đúng câu đã hỏi khách lúc
    # đó; đồng thời tránh phải khai phụ thuộc cứng sang seroto_education chỉ vì 1 field
    # liên kết (xem SerotoCourseRegistration._get_course_questions() ở trên).
    question = fields.Char(string='Câu hỏi', required=True)
    answer = fields.Char(string='Trả lời')


class SerotoCourseRegistrationBasicAnswer(models.Model):
    _name = 'seroto.course.registration.basic.answer'
    _description = 'Trả lời câu hỏi cơ bản (Phiếu đăng ký khóa học)'
    _order = 'id'

    # Model RIÊNG với seroto.course.registration.answer ("Câu hỏi chuyên sâu") - câu hỏi
    # ở đây trả lời NGAY Ở BƯỚC 1 "Thông tin cơ bản", trước khi Phiếu đăng ký tồn tại.
    registration_id = fields.Many2one(
        'seroto.course.registration', string='Phiếu đăng ký', required=True, ondelete='cascade',
    )
    question = fields.Char(string='Câu hỏi', required=True)
    answer = fields.Char(string='Trả lời')


class SerotoCourseRegistrationCategoryInfo(models.Model):
    _name = 'seroto.course.registration.category.info'
    _description = 'Thông tin theo diện đăng ký (Phiếu đăng ký khóa học)'
    _order = 'id'

    registration_id = fields.Many2one(
        'seroto.course.registration', string='Phiếu đăng ký', required=True, ondelete='cascade',
    )
    # label/value dạng CHUNG (không khai field riêng cho từng thông tin của diện y
    # tế/tổ chức phi lợi nhuận) - controller (create_registration) tự ghép đúng nhãn cố
    # định theo từng diện lúc tạo phiếu, hiển thị dạng list y hệt seroto.course.
    # registration.answer/"Câu hỏi chuyên sâu" ở trên.
    label = fields.Char(string='Thông tin', required=True)
    value = fields.Char(string='Nội dung')
