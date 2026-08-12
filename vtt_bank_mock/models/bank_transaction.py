import hashlib
import hmac
import json
import logging
import secrets

import requests

from odoo import models, fields, _

_logger = logging.getLogger(__name__)

# Timeout gọi webhook - server "ngân hàng" (chính module này) không nên treo cả request
# xác nhận thanh toán của khách chỉ vì bên nhận (module gọi module này) phản hồi chậm.
NOTIFY_TIMEOUT = 10


class BankMockTransaction(models.Model):
    _name = 'bank.mock.transaction'
    _description = 'Giao dịch ngân hàng giả lập (dev/test - xem vtt_bank_mock)'
    _order = 'create_date desc'

    # Module gọi (vd vtt_seroto_website) tự đặt reference để đối chiếu ngược lại đúng
    # bản ghi của nó khi nhận webhook - vtt_bank_mock không cần biết ý nghĩa chuỗi này.
    reference = fields.Char(string='Mã tham chiếu', required=True, index=True)
    amount = fields.Float(string='Số tiền')
    description = fields.Char(string='Nội dung chuyển khoản')

    notify_url = fields.Char(string='Webhook nhận kết quả', required=True)
    # Secret do BÊN GỌI cung cấp lúc tạo giao dịch (không phải secret của riêng module
    # này) - dùng để ký HMAC lúc gọi webhook, bên nhận tự đối chiếu lại vì chính nó biết
    # secret này. Nhờ vậy vtt_bank_mock không cần lưu/thoả thuận secret dùng chung nào.
    notify_secret = fields.Char(string='Khóa ký webhook', required=True)
    notified = fields.Boolean(string='Đã gọi webhook thành công', default=False)

    # Bảo vệ trang "thanh toán" (checkout) - không cho đoán ID để xem/thao tác giao dịch
    # của người khác.
    checkout_token = fields.Char(
        string='Mã truy cập trang thanh toán', required=True, copy=False, readonly=True,
        default=lambda self: secrets.token_urlsafe(24),
    )

    # CHỈ 2 trạng thái - giống hệt 1 mã QR chuyển khoản ngân hàng thật: chưa quét/quét
    # nhưng chưa thanh toán thì mã VẪN CÒN HIỆU LỰC để quét lại, không có khái niệm
    # "hủy" nào làm mã chết hẳn từ phía người bán. "paid" là trạng thái cuối cùng
    # (không quay lại "pending" được) vì 1 giao dịch đã thanh toán rồi thì không thanh
    # toán lại được nữa.
    status = fields.Selection(
        [('pending', 'Chờ thanh toán'), ('paid', 'Đã thanh toán')],
        string='Trạng thái', default='pending', required=True,
    )
    confirmed_at = fields.Datetime(string='Thời điểm xác nhận')

    # Con trỏ TỔNG QUÁT (không hard-code tên model cụ thể nào) tới bản ghi đã tạo giao
    # dịch này - module gọi (vd vtt_seroto_website) tự truyền vào lúc create(), CHỈ để
    # dựng nút "Xem bản ghi liên quan" (action_view_related_record) - vtt_bank_mock vẫn
    # không cần biết ý nghĩa/model đó là gì, giữ đúng thiết kế module độc lập ban đầu.
    related_res_model = fields.Char(string='Model liên kết')
    related_res_id = fields.Integer(string='ID bản ghi liên kết')

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '[GD-%d]' % rec.id if isinstance(rec.id, int) else _('Giao dịch mới')

    def _get_checkout_url(self):
        self.ensure_one()
        return '%s/bank-mock/checkout/%s/%s' % (self.get_base_url(), self.id, self.checkout_token)

    def action_view_related_record(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.related_res_model,
            'res_id': self.related_res_id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_confirm(self):
        for transaction in self:
            if transaction.status != 'pending':
                continue
            transaction.write({'status': 'paid', 'confirmed_at': fields.Datetime.now()})
            transaction._notify()

    def _notify(self):
        """Gọi webhook báo kết quả về cho module đã tạo giao dịch - CỐ TÌNH build request
        giống hệt hình dạng 1 webhook ngân hàng/cổng thanh toán thật sẽ gửi (JSON body +
        chữ ký HMAC trong header) để phía nhận không phải đổi cách xác thực khi thay
        bằng tích hợp thật, chỉ đổi nơi gọi tới.
        """
        self.ensure_one()

        payload = {
            'reference': self.reference,
            'amount': self.amount,
            'status': self.status,
            'confirmed_at': fields.Datetime.to_string(self.confirmed_at),
        }
        body = json.dumps(payload, sort_keys=True).encode()
        signature = hmac.new(self.notify_secret.encode(), body, hashlib.sha256).hexdigest()

        _logger.info(
            'Đang gọi webhook cho giao dịch giả lập ID=%s (reference=%s) -> %s',
            self.id, self.reference, self.notify_url,
        )

        # Gọi đồng bộ, chặn ngay trong request xác nhận thanh toán của khách - chấp nhận
        # được cho mục đích giả lập (webhook gọi lại chính server đang chạy). Nếu thay
        # bằng tích hợp thật với độ trễ/độ tin cậy khác, cân nhắc đẩy việc gọi webhook
        # ra hàng đợi/cron thay vì gọi đồng bộ như ở đây.
        #
        # Header X-Odoo-Database: request tự gọi này KHÔNG có cookie phiên đăng nhập
        # (đúng như 1 webhook thật sẽ không có) - trên môi trường dev có NHIỀU database
        # cùng lúc và không khai báo dbfilter/db_name cố định trong odoo.conf, Odoo
        # KHÔNG tự suy ra được nên phục vụ request bằng database nào, trả về lỗi "No
        # database is selected" (đã kiểm chứng thực tế). self.env.cr.dbname luôn đúng là
        # database hiện tại của chính request đang xử lý (lúc khách bấm "Xác nhận"), nên
        # dùng lại để tự chỉ định - production chỉ chạy 1 database/domain thì không cần
        # quan tâm header này (Odoo tự suy ra được, có header cũng không hại gì).
        try:
            response = requests.post(
                self.notify_url,
                data=body,
                headers={
                    'Content-Type': 'application/json',
                    'X-Bank-Mock-Signature': signature,
                    'X-Odoo-Database': self.env.cr.dbname,
                },
                timeout=NOTIFY_TIMEOUT,
            )
            response.raise_for_status()
            self.notified = True
            _logger.info('Gọi webhook thành công cho giao dịch giả lập ID=%s', self.id)
        except Exception:
            _logger.exception(
                'Gửi webhook thất bại cho giao dịch giả lập ID=%s (reference=%s, notify_url=%s)',
                self.id, self.reference, self.notify_url,
            )
