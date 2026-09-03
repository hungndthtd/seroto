import logging
import secrets

from odoo import models, fields

_logger = logging.getLogger(__name__)

# Tham số hệ thống quyết định nhánh thanh toán - CHỈ đọc/ghi qua
# seroto.payment.dev.switch.wizard (khóa base.group_system). Giá trị 'bank_mock' =
# dùng cổng giả lập; bất kỳ giá trị nào khác (kể cả chưa từng set) = payOS thật.
DEV_SWITCH_PARAM = 'vtt_payment_dev_switch.enabled'


class SerotoCourseRegistration(models.Model):
    _inherit = 'seroto.course.registration'

    # 2 field TỔNG QUÁT lưu link/QR thanh toán bất kể provider nào - CHỈ được ghi khi
    # dùng nhánh giả lập (xem _create_dev_bank_mock_transaction). Nhánh payOS thật
    # (vtt_seroto_website gốc, super()._create_payment_transaction()) không đụng tới 2
    # field này - _get_checkout_url/_get_checkout_qr_url bên dưới chỉ ưu tiên đọc
    # trước khi rơi về đúng hành vi gốc, nên payOS thật không bị ảnh hưởng gì.
    #
    # payment_transaction_ref / payment_provider_label định nghĩa Ở FILE GỐC
    # (vtt_seroto_website/models/course_registration.py) - đây là field tổng quát cho
    # MỌI cổng thanh toán, không riêng gì nhánh dev, nên KHÔNG đặt ở module dev-only
    # này (production không cài module này vẫn cần thấy đúng field này khi dùng payOS
    # thật). checkout_url ở đây chỉ phục vụ link/QR hiển thị cho KHÁCH lúc thanh toán
    # (JS wizard đọc qua _get_checkout_url()), khác với payment_transaction_ref/
    # payment_provider_label là 2 field NHÂN VIÊN xem trên form backend.
    checkout_url = fields.Char(readonly=True, copy=False)
    checkout_qr_url = fields.Char(readonly=True, copy=False)

    def _get_checkout_url(self):
        self.ensure_one()
        return self.checkout_url or super()._get_checkout_url()

    def _get_checkout_qr_url(self):
        self.ensure_one()
        return self.checkout_qr_url or super()._get_checkout_qr_url()

    def _create_payment_transaction(self):
        self.ensure_one()
        if self._dev_switch_active():
            _logger.warning(
                'Phiếu %s dùng cổng thanh toán GIẢ LẬP (vtt_bank_mock, dev) - '
                'KHÔNG PHẢI payOS thật. Đổi lại "Cổng thanh toán" thành payOS nếu '
                'đây không phải là ý muốn.', self.code,
            )
            return self._create_dev_bank_mock_transaction()
        return super()._create_payment_transaction()

    def _dev_switch_active(self):
        """Bật khi VÀ CHỈ KHI tham số hệ thống được set tường minh = 'bank_mock' -
        mặc định (chưa từng set) luôn coi như tắt. Chỉ chỉnh được qua wizard khóa
        base.group_system (xem models/dev_switch_wizard.py).
        """
        return self.env['ir.config_parameter'].sudo().get_param(DEV_SWITCH_PARAM) == 'bank_mock'

    def _create_dev_bank_mock_transaction(self):
        self.ensure_one()
        amount = self.course_id.product_id.list_price if self.course_id.product_id else 0
        transaction = self.env['bank.mock.transaction'].sudo().create({
            'reference': self.code,
            'amount': amount,
            'description': self.code,
            'notify_url': '%s/seroto/course-registration/dev-bank-mock-webhook' % self.get_base_url(),
            # Random MỖI giao dịch, không bao giờ trả về client - controllers/
            # dev_bank_mock_webhook.py tự tra lại đúng bản ghi này để đối chiếu chữ ký,
            # không tin bất kỳ giá trị "status" nào client tự khai.
            'notify_secret': secrets.token_urlsafe(32),
            'related_res_model': self._name,
            'related_res_id': self.id,
        })
        self.checkout_url = transaction._get_checkout_url()
        self.checkout_qr_url = False  # cổng giả lập không có QR thật
        self.payment_transaction_ref = 'bank.mock.transaction,%s' % transaction.id
        return transaction

    def _mark_paid_and_process(self):
        """Dùng RIÊNG cho webhook giả lập (controllers/dev_bank_mock_webhook.py) sau
        khi đã xác thực chữ ký HMAC. CỐ TÌNH không dùng chung với _payos_on_paid gốc
        (vtt_seroto_website/models/course_registration.py) dù 2 dòng logic bên dưới
        giống hệt nhau - đánh đổi 1 chút trùng lặp để đổi lấy việc không phải sửa 1
        byte nào trong file gốc của vtt_seroto_website.
        """
        self.ensure_one()
        if self.payment_status != 'paid':
            self.payment_status = 'paid'
        self._auto_process_payment()
