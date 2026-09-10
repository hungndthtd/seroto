# -*- coding: utf-8 -*-

import logging

from odoo import http
from odoo.http import request

from ..tools import payos_client

_logger = logging.getLogger(__name__)


class PayOSWebhookController(http.Controller):

    # Địa chỉ CỐ ĐỊNH - khác với vtt_bank_mock (mỗi giao dịch tự khai 1 notify_url
    # riêng), payOS bắt buộc khai báo SẴN 1 địa chỉ webhook duy nhất trên hệ thống quản
    # trị của họ (https://my.payos.vn) - phải tự đăng ký đúng URL này ở đó (1 lần).
    #
    # Vì CHỈ có đúng 1 địa chỉ webhook cho cả tài khoản, route này PHỤC VỤ CHUNG cho cả
    # module vtt_payment_payos (payOS khai báo chuẩn payment.provider cho Shop/eCommerce,
    # cài thêm sau này, cùng dùng chung 1 tài khoản payOS thật) - xem
    # _try_process_payment_provider_tx() bên dưới, KHÔNG cần đăng ký thêm URL nào khác.
    #
    # Xác thực qua SDK chính thức (payos_client.verify_webhook -> client.webhooks.verify)
    # - đúng theo mẫu code payOS cung cấp: verify() ném lỗi -> trả 400 "Invalid webhook";
    # verify() qua -> LUÔN trả 200 "OK", kể cả khi order_code không khớp giao dịch nào
    # trong hệ thống (payOS tự gọi thử URL này lúc đăng ký Webhook trên my.payos.vn bằng
    # 1 order_code mẫu - không được coi đó là lỗi, chỉ log lại).
    @http.route('/payos/webhook', type='http', auth='public', methods=['POST'], csrf=False)
    def webhook(self, **kwargs):
        client_id, api_key, checksum_key = request.env['payos.transaction'].sudo()._get_credentials()

        try:
            webhook_data = payos_client.verify_webhook(
                client_id, api_key, checksum_key, request.httprequest.get_data(),
            )
        except Exception:
            _logger.exception('Webhook payOS không hợp lệ.')
            return request.make_json_response({'message': 'Invalid webhook'}, status=400)

        transaction = request.env['payos.transaction'].sudo().search(
            [('order_code', '=', webhook_data.order_code)], limit=1,
        )
        if transaction:
            transaction._process_paid(webhook_data)
        elif not self._try_process_payment_provider_tx(webhook_data):
            _logger.info('Webhook payOS: không tìm thấy giao dịch order_code=%s', webhook_data.order_code)

        return request.make_json_response({'message': 'OK'}, status=200)

    def _try_process_payment_provider_tx(self, webhook_data):
        """Không khớp payos.transaction (module này) - thử coi order_code là của module
        vtt_payment_payos (payOS khai báo như payment.provider CHUẨN cho Shop/eCommerce,
        dùng CHUNG đúng 1 ir.sequence payos.transaction.order_code với module này - xem
        vtt_payment_payos/const.py, PAYOS_ORDER_CODE_SEQUENCE - nên order_code không cần
        offset/khoảng cách gì, tra thẳng theo field payos_order_code trên payment.transaction).
        An toàn dù module đó chưa cài: model/field không tồn tại hay order_code không khớp
        bản ghi nào đều coi là "không xử lý được", trả về False, KHÔNG ném lỗi.
        """
        try:
            PaymentTx = request.env['payment.transaction']
        except KeyError:
            return False
        if 'payos_order_code' not in PaymentTx._fields:
            return False
        tx = PaymentTx.sudo().search([('payos_order_code', '=', webhook_data.order_code)], limit=1)
        if not tx:
            return False
        PaymentTx.sudo()._process('payos', {'reference': tx.reference})
        return True
