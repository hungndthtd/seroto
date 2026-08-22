import logging
import secrets

from odoo import api, models, fields, _

_logger = logging.getLogger(__name__)


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
    class_id = fields.Many2one(
        'academic.class', string='Lớp học', domain="[('course_id', '=', course_id)]",
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
    answer_ids = fields.One2many(
        'seroto.course.registration.answer', 'registration_id',
        string='Câu trả lời (Thông tin chuyên sâu)',
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

    @api.depends('course_id.question_ids.question', 'answer_ids.question', 'answer_ids.answer',
                 'partner_name', 'email', 'phone')
    def _compute_is_complete(self):
        for rec in self:
            if not (rec.partner_name and rec.email and rec.phone):
                rec.is_complete = False
                continue
            required_questions = rec.course_id.question_ids.mapped('question') if rec.course_id else []
            answered = {a.question for a in rec.answer_ids if (a.answer or '').strip()}
            rec.is_complete = all(q in answered for q in required_questions)

    # Cho phép khách xem/tiếp tục phiếu qua link trong email mà KHÔNG cần đăng nhập -
    # so khớp token thay vì id để không ai đoán được link phiếu của người khác.
    access_token = fields.Char(
        string='Mã truy cập phiếu', required=True, copy=False, readonly=True,
        default=lambda self: secrets.token_urlsafe(24),
    )

    # Giao dịch thanh toán payOS (module vtt_payos - xem _create_payment_transaction())
    # tương ứng với phiếu này.
    payos_transaction_id = fields.Many2one(
        'payos.transaction', string='Giao dịch payOS', copy=False,
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
        return records

    def action_confirm(self):
        self.write({'state': 'confirmed'})

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
            order_line_vals.append((0, 0, {
                'product_id': self.course_id.product_id.id,
                'class_id': self.class_id.id if self.class_id else False,
                'student_id': student.id,
            }))

        order = self.env['sale.order'].sudo().create({
            'partner_id': registrant.id,
            'order_line': order_line_vals,
        })
        self.sale_order_id = order.id
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
                # Mỗi lựa chọn 1 dòng trên form Khóa học -> tách thành mảng cho JS dựng
                # dropdown/nhóm ô chọn (xem question_ids trên academic.course.question -
                # KHÔNG dùng dấu phẩy để tránh đụng lựa chọn tự nó chứa dấu phẩy).
                'options': [
                    line.strip() for line in (question.options or '').split('\n') if line.strip()
                ],
            }
            for question in course.question_ids
        ]

    def _create_payment_transaction(self):
        """Tạo link thanh toán payOS thật cho phiếu này - khách quét QR hoặc mở
        checkout_url để thanh toán. payOS gọi thẳng về payos_transaction._process_paid()
        (qua webhook cố định /payos/webhook, module vtt_payos) rồi tự tìm tới
        _payos_on_paid() ở trên theo đúng quy ước related_res_model/related_res_id.
        """
        self.ensure_one()

        # Lấy đúng giá bán hiện tại của Sản phẩm liên kết (academic.course.product_id) -
        # course_id đã tự suy ra từ course_name lúc create() (nếu khớp được tên khóa
        # học). Không khớp được khóa học hoặc khóa học chưa gắn sản phẩm thì để 0đ (thà
        # rõ ràng là chưa xác định được giá còn hơn hiện nhầm số của phiếu khác).
        amount = 0
        if self.course_id and self.course_id.product_id:
            amount = self.course_id.product_id.list_price

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
        email_from = self.env.company.email or self.env.user.email

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
