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
        else:
            _logger.info('Webhook payOS: không tìm thấy giao dịch order_code=%s', webhook_data.order_code)

        return request.make_json_response({'message': 'OK'}, status=200)
