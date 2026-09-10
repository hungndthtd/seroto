# -*- coding: utf-8 -*-

from urllib.parse import quote

from odoo import api, fields, models
from odoo.tools.urls import urljoin

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.vtt_payos.tools import payos_client

from ..const import PAYOS_ORDER_CODE_SEQUENCE
from ..controllers.main import PayosPaymentController

_logger = get_payment_logger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    payos_qr_code = fields.Text(
        string='Dữ liệu mã QR payOS (VietQR)', readonly=True, copy=False,
    )
    # order_code KHÔNG suy ra được từ id (khác bản trước dùng offset + id) - phải tự lưu lại
    # để webhook tra ngược đúng giao dịch (xem vtt_payos/controllers/payos_webhook.py,
    # _try_process_payment_provider_tx). index=True vì đây là điều kiện search() của webhook.
    payos_order_code = fields.Integer(
        string='Mã đơn payOS (orderCode)', readonly=True, copy=False, index=True,
    )

    def _get_specific_rendering_values(self, processing_values):
        """Override của `payment` để trả về giá trị hiển thị riêng cho payOS.

        Note: self.ensure_one() từ `_get_processing_values`
        """
        if self.provider_code != 'payos':
            return super()._get_specific_rendering_values(processing_values)

        return {
            'api_url': PayosPaymentController._process_url,
            'reference': self.reference,
        }

    def _payos_create_payment_link(self):
        """Gọi payOS tạo link+QR thật, lưu lại payos_qr_code, rồi chuyển giao dịch sang
        pending. Gọi từ controller (POST vào api_url) NGAY khi khách bấm Thanh toán - mẫu
        đúng theo payment_custom (chỉ _set_pending() khi controller đã thực sự xử lý xong,
        không set ngay trong _get_specific_rendering_values).
        """
        self.ensure_one()
        provider = self.provider_id
        # Dùng CHUNG credentials đã cấu hình sẵn ở vtt_payos (menu payOS > Cấu hình) - cùng
        # 1 tài khoản payOS thật với module đó, tránh phải nhập trùng 2 nơi/rủi ro lệch khóa.
        # _get_credentials() tự raise UserError rõ ràng nếu vtt_payos CHƯA được cấu hình.
        client_id, api_key, checksum_key = self.env['payos.transaction']._get_credentials()
        # Dùng CHUNG đúng 1 ir.sequence với vtt_payos (payos.transaction.order_code) - xem
        # const.py, PAYOS_ORDER_CODE_SEQUENCE - không cần offset/khoảng cách nào giữa 2 module.
        order_code = int(self.env['ir.sequence'].sudo().next_by_code(PAYOS_ORDER_CODE_SEQUENCE))
        return_url = urljoin(provider.get_base_url(), '/payment/status')
        result = payos_client.create_payment_link(
            client_id, api_key, checksum_key,
            order_code=order_code,
            amount=int(self.amount),
            # payOS giới hạn "description" tối đa 25 ký tự - cắt ngắn phòng reference dài.
            description=self.reference[:25],
            return_url=return_url,
            cancel_url=return_url,
        )
        self.payos_order_code = order_code
        self.payos_qr_code = result.get('qr_code')
        self._set_pending()

    def payos_get_qr_image_url(self):
        """Mirror đúng kỹ thuật _get_qr_image_url() của payos.transaction (vtt_payos): dùng
        lại route /report/barcode/ có sẵn của Odoo core để vẽ QR từ chuỗi VietQR - KHÔNG
        import model payos.transaction (chỉ tái dùng kỹ thuật, tránh phụ thuộc chéo không
        cần thiết vào model của module khác).
        """
        self.ensure_one()
        if not self.payos_qr_code:
            return False
        return '/report/barcode/?barcode_type=QR&value=%s&width=200&height=200' % quote(
            self.payos_qr_code, safe='',
        )

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        """Override của `payment` để trích reference từ payment_data.

        Note: `payment_data` ở đây LUÔN là dict do
        vtt_payos/controllers/payos_webhook.py::_try_process_payment_provider_tx tự dựng
        (đã tự tra ngược payos_order_code -> giao dịch -> reference), KHÔNG phải object
        webhook_data thô của SDK payos.
        """
        if provider_code != 'payos':
            return super()._extract_reference(provider_code, payment_data)
        return payment_data.get('reference')

    def _extract_amount_data(self, payment_data):
        """Override của `payment` - bỏ qua kiểm tra số tiền cho payOS.

        SDK "payos" (client.webhooks.verify) chưa có tài liệu xác nhận đầy đủ payload đối
        soát để so khớp số tiền an toàn (hạn chế đã ghi nhận sẵn ở
        vtt_payos/models/payos_transaction.py) - mirror đúng cách payment_custom xử lý cho
        Wire Transfer (return None = bỏ qua bước _validate_amount).
        """
        if self.provider_code != 'payos':
            return super()._extract_amount_data(payment_data)
        return None

    def _apply_updates(self, payment_data):
        """Override của `payment` để cập nhật giao dịch sau khi webhook xác nhận đã thanh toán."""
        if self.provider_code != 'payos':
            return super()._apply_updates(payment_data)

        _logger.info("Xác nhận thanh toán payOS cho giao dịch %s.", self.reference)
        self._set_done()
