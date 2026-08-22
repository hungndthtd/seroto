# -*- coding: utf-8 -*-

import logging
from urllib.parse import quote

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..tools import payos_client

_logger = logging.getLogger(__name__)


class PayOSTransaction(models.Model):
    _name = 'payos.transaction'
    _description = 'Giao dịch thanh toán payOS'
    _order = 'create_date desc'

    # Mã số nguyên duy nhất gửi cho payOS (orderCode) - payOS BẮT BUỘC phải là số, khác
    # với reference dạng chuỗi ("PDK-123") của vtt_bank_mock. Sinh qua ir.sequence
    # (payos.transaction.order_code) thay vì dùng thẳng ID bản ghi gốc, để cho phép tạo
    # lại 1 link thanh toán MỚI cho cùng 1 bản ghi gốc nếu link trước hết hạn/bị hủy -
    # payOS không cho tái dùng y nguyên 1 orderCode cho lần thử thanh toán khác.
    order_code = fields.Integer(string='Mã đơn (payOS)', required=True, index=True, copy=False)
    amount = fields.Integer(string='Số tiền', required=True)
    description = fields.Char(string='Nội dung chuyển khoản')

    checkout_url = fields.Char(string='Link thanh toán', readonly=True)
    qr_code = fields.Text(string='Dữ liệu mã QR (chuỗi VietQR)', readonly=True)
    payment_link_id = fields.Char(string='Mã link (payOS)', readonly=True)

    status = fields.Selection([
        ('pending', 'Chờ thanh toán'),
        ('paid', 'Đã thanh toán'),
    ], string='Trạng thái', default='pending', required=True)
    confirmed_at = fields.Datetime(string='Thời điểm xác nhận')

    # Toàn bộ thông tin đối soát payOS trả về trong webhook_data lúc xác nhận đã thanh
    # toán (client.webhooks.verify) - phục vụ tra cứu/đối chiếu với sao kê ngân hàng
    # thật sau này, KHÔNG chỉ dừng ở status/confirmed_at như bản đầu. Dùng getattr khi
    # đọc (xem _extract_webhook_vals) vì SDK "payos" chưa có tài liệu xác nhận đầy đủ
    # 100% tên field trên đối tượng webhook_data - field nào SDK không trả về/đổi tên
    # thì để trống, không làm vỡ việc xác nhận thanh toán.
    webhook_description = fields.Char(
        string='Nội dung chuyển khoản (ngân hàng ghi nhận)', readonly=True,
        help='Nội dung đầy đủ ngân hàng thực sự ghi nhận trên giao dịch - có thể khác '
             'với "Nội dung chuyển khoản" đã gửi payOS lúc tạo link vì payOS/ngân hàng '
             'có thể tự thêm tiền tố riêng vào trước.',
    )
    bank_reference = fields.Char(string='Mã tham chiếu ngân hàng', readonly=True)
    bank_transaction_datetime = fields.Char(string='Thời điểm ngân hàng ghi nhận', readonly=True)
    counter_account_name = fields.Char(string='Tên tài khoản chuyển', readonly=True)
    counter_account_number = fields.Char(string='Số tài khoản chuyển', readonly=True)
    counter_account_bank_name = fields.Char(string='Ngân hàng của người chuyển', readonly=True)

    # Con trỏ TỔNG QUÁT (không hard-code tên model cụ thể) tới bản ghi đã tạo giao dịch
    # này - đúng quy ước đã dùng ở bank.mock.transaction (module vtt_bank_mock), để bên
    # gọi (vd vtt_seroto_website) không cần khai phụ thuộc ngược vào module này chỉ vì 1
    # field liên kết. Khi giao dịch chuyển "paid", tự tìm và gọi method quy ước
    # "_payos_on_paid(transaction)" trên bản ghi này nếu có - xem _notify_related_record().
    related_res_model = fields.Char(string='Model liên kết')
    related_res_id = fields.Integer(string='ID bản ghi liên kết')

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '[PO-%d]' % rec.id if isinstance(rec.id, int) else _('Giao dịch payOS mới')

    def action_view_related_record(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.related_res_model,
            'res_id': self.related_res_id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def _get_credentials(self):
        ICP = self.env['ir.config_parameter'].sudo()
        client_id = ICP.get_param('vtt_payos.client_id')
        api_key = ICP.get_param('vtt_payos.api_key')
        checksum_key = ICP.get_param('vtt_payos.checksum_key')
        if not (client_id and api_key and checksum_key):
            raise UserError(_(
                'Chưa cấu hình đủ Client ID / API Key / Checksum Key của payOS '
                '(menu payOS > Cấu hình).'
            ))
        return client_id, api_key, checksum_key

    def _get_qr_image_url(self):
        """Ảnh QR (PNG) mã hóa đúng chuỗi VietQR payOS trả về - dùng lại route
        /report/barcode/ có sẵn của Odoo core, giống hệt cách course_registration.py
        (module vtt_seroto_website) đang làm với checkout_url của vtt_bank_mock.
        """
        self.ensure_one()
        if not self.qr_code:
            return False
        return '/report/barcode/?barcode_type=QR&value=%s&width=200&height=200' % quote(self.qr_code, safe='')

    @api.model
    def create_for_record(self, amount, description, related_record, return_url, cancel_url):
        """Tạo 1 giao dịch thanh toán payOS mới, gắn với related_record bất kỳ (model
        nào cũng được, xem related_res_model/related_res_id ở trên).
        """
        client_id, api_key, checksum_key = self._get_credentials()
        order_code = int(self.env['ir.sequence'].next_by_code('payos.transaction.order_code'))

        result = payos_client.create_payment_link(
            client_id, api_key, checksum_key,
            order_code=order_code, amount=int(amount), description=description,
            return_url=return_url, cancel_url=cancel_url,
        )

        return self.create({
            'order_code': order_code,
            'amount': int(amount),
            'description': description,
            'checkout_url': result.get('checkout_url'),
            'qr_code': result.get('qr_code'),
            'payment_link_id': result.get('payment_link_id'),
            'related_res_model': related_record._name,
            'related_res_id': related_record.id,
        })

    def _process_paid(self, webhook_data=None):
        """Đánh dấu đã thanh toán + báo ngược cho bản ghi liên quan - gọi từ webhook
        (controllers/payos_webhook.py, có kèm webhook_data để lưu lại đầy đủ thông tin
        đối soát) lẫn từ cron đối soát (_cron_reconcile_pending, hiện chưa có
        webhook_data tương đương). Idempotent (gọi lại nhiều lần trên 1 giao dịch đã
        "paid" không làm gì thêm, không ghi đè lại thông tin đối soát đã có).
        """
        for rec in self:
            if rec.status == 'paid':
                continue
            vals = {'status': 'paid', 'confirmed_at': fields.Datetime.now()}
            if webhook_data is not None:
                vals.update(rec._extract_webhook_vals(webhook_data))
            rec.write(vals)
            rec._notify_related_record()

    def _extract_webhook_vals(self, webhook_data):
        """Trích các field đối soát từ đối tượng webhook_data do SDK "payos" trả về
        (client.webhooks.verify) - dùng getattr phòng khi SDK thiếu/đổi tên field nào
        đó, tránh vỡ luôn cả việc xác nhận thanh toán chỉ vì thiếu 1 field phụ.
        """
        return {
            'webhook_description': getattr(webhook_data, 'description', None),
            'bank_reference': getattr(webhook_data, 'reference', None),
            'bank_transaction_datetime': str(getattr(webhook_data, 'transaction_date_time', '') or '') or None,
            'counter_account_name': getattr(webhook_data, 'counter_account_name', None),
            'counter_account_number': getattr(webhook_data, 'counter_account_number', None),
            'counter_account_bank_name': getattr(webhook_data, 'counter_account_bank_name', None),
        }

    def _notify_related_record(self):
        self.ensure_one()
        if not (self.related_res_model and self.related_res_id):
            return
        record = self.env[self.related_res_model].sudo().browse(self.related_res_id).exists()
        if not record:
            return
        if hasattr(record, '_payos_on_paid'):
            record._payos_on_paid(self)
        else:
            _logger.warning(
                'payos.transaction ID=%s liên kết tới %s(%s) nhưng model đó chưa có '
                'method _payos_on_paid() - không có gì được thông báo.',
                self.id, self.related_res_model, self.related_res_id,
            )

    @api.model
    def _cron_reconcile_pending(self):
        """TẠM VÔ HIỆU HÓA (xem data/ir_cron_data.xml, active=False) - tài liệu SDK
        "payos" chính thức chưa xác nhận rõ phương thức tra cứu trạng thái 1 link thanh
        toán theo order_code (chỉ mới xác nhận payment_requests.create và
        webhooks.verify). Không đoán bừa tên phương thức để tránh gọi sai gây lỗi lặp
        lại mỗi kỳ chạy cron. Khi có tài liệu/API xác nhận, hoàn thiện hàm này rồi bật
        lại cron tương ứng.
        """
        _logger.info('_cron_reconcile_pending: chưa triển khai (chờ xác nhận API tra cứu trạng thái từ payOS SDK) - bỏ qua.')
