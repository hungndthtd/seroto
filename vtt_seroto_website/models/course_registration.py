import logging
import secrets
from urllib.parse import quote

from odoo import api, models, fields, _

_logger = logging.getLogger(__name__)


class SerotoCourseRegistration(models.Model):
    _name = 'seroto.course.registration'
    _description = 'Phiếu đăng ký khóa học (modal "Đăng ký ngay" nhiều bước)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    course_name = fields.Char(string='Khóa học', required=True)
    # Many2one thật, tự suy ra từ course_name lúc tạo (xem create()) - để lọc class_id,
    # tự điền lớp nhận đăng ký mặc định, và sau này tạo sale.order.line đúng sản phẩm.
    course_id = fields.Many2one('academic.course', string='Khóa học (liên kết)')
    class_id = fields.Many2one(
        'academic.class', string='Lớp học', domain="[('course_id', '=', course_id)]",
    )
    partner_name = fields.Char(string='Họ tên', required=True)
    email = fields.Char(string='Email', required=True)
    phone = fields.Char(string='Số điện thoại', required=True)
    # Chỉ tạo/gắn res.partner thật lúc NV xác nhận hoặc tạo đơn hàng (action_confirm/
    # action_create_sale_order) - tránh tạo rác liên hệ cho các phiếu bị từ chối/hủy.
    partner_id = fields.Many2one('res.partner', string='Khách hàng', readonly=True, copy=False)
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

    # Giao dịch thanh toán giả lập (module vtt_bank_mock, dev/test - xem
    # _create_bank_transaction()) tương ứng với phiếu này.
    bank_transaction_id = fields.Many2one(
        'bank.mock.transaction', string='Giao dịch thanh toán (giả lập)', copy=False,
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
            rec.display_name = '[PDK-%d]' % rec.id if isinstance(rec.id, int) else _('Phiếu đăng ký mới')

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
        return super().create(vals_list)

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

    def action_create_sale_order(self):
        self.ensure_one()
        partner = self._find_or_create_partner()

        order_line_vals = []
        if self.course_id.product_id:
            order_line_vals.append((0, 0, {
                'product_id': self.course_id.product_id.id,
                'class_id': self.class_id.id if self.class_id else False,
                'student_id': partner.id,
            }))

        order = self.env['sale.order'].sudo().create({
            'partner_id': partner.id,
            'order_line': order_line_vals,
        })
        self.sale_order_id = order.id

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': order.id,
            'view_mode': 'form',
            'target': 'current',
        }

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

    def _create_bank_transaction(self):
        """Tạo giao dịch thanh toán để khách quét mã/mở trang thanh toán.

        THAY KHI CÓ API NGÂN HÀNG THẬT: đổi nội dung hàm này sang gọi API tạo giao
        dịch/lấy mã QR của ngân hàng/cổng thanh toán thật (vd MB Bank, VNPay, Casso...)
        thay vì tạo bank.mock.transaction - miễn là vẫn trả về 1 URL cho khách "thanh
        toán" thì _get_checkout_url()/luồng JS phía dưới không cần đổi gì thêm.
        """
        self.ensure_one()

        transaction = self.env['bank.mock.transaction'].sudo().create({
            # "PDK-<id>" khớp đúng mã hiển thị của phiếu (_compute_display_name ở trên,
            # "[PDK-<id>]") - webhook (controllers/course_registration.py, _REFERENCE_RE)
            # tách lại đúng ID này để tìm về phiếu.
            'reference': 'PDK-%s' % self.id,
            # TODO: trang chủ (s_trang_chu_course.xml) hiện chỉ truyền tên khóa học,
            # chưa có học phí -> tạm để 0đ, cần bổ sung data-price khi có nhu cầu thanh
            # toán số tiền cụ thể.
            'amount': 0,
            'description': '%s - %s' % (self.course_name, self.phone),
            'notify_url': '%s/seroto/course-registration/webhook/bank-notify' % self.get_base_url(),
            'notify_secret': self.access_token,
            # Chỉ để vtt_bank_mock dựng nút "Xem bản ghi liên quan" - module đó vẫn
            # không cần biết ý nghĩa model này là gì.
            'related_res_model': 'seroto.course.registration',
            'related_res_id': self.id,
        })
        self.bank_transaction_id = transaction.id
        return transaction

    def _get_checkout_url(self):
        self.ensure_one()
        return self.bank_transaction_id._get_checkout_url() if self.bank_transaction_id else False

    def _get_checkout_qr_url(self):
        """Ảnh QR (PNG) mã hóa checkout_url - dùng route /report/barcode/ có sẵn của
        Odoo core (module "web", thư viện reportlab) để sinh ảnh, KHÔNG cần cài thêm
        gì. Khách quét bằng app ngân hàng bất kỳ (demo - vẫn dẫn tới trang giả lập, xem
        vtt_bank_mock) thay vì phải bấm nút mở tab trên cùng thiết bị.
        """
        self.ensure_one()
        checkout_url = self._get_checkout_url()
        if not checkout_url:
            return False
        return '/report/barcode/?barcode_type=QR&value=%s&width=200&height=200' % quote(checkout_url, safe='')

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
