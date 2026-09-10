# -*- coding: utf-8 -*-

from odoo.http import Controller, request, route


class PayosPaymentController(Controller):
    _process_url = '/payment/payos/process'

    # KHÔNG có route webhook riêng ở đây - payOS chỉ cho khai báo 1 địa chỉ webhook DUY
    # NHẤT cho cả tài khoản trên my.payos.vn (đã đăng ký sẵn /payos/webhook của vtt_payos).
    # Webhook cho giao dịch của module này (payment.transaction, order_code >= 10_000_000,
    # xem const.py) được PayOSWebhookController.webhook() của vtt_payos tự nhận diện và xử
    # lý luôn - xem vtt_payos/controllers/payos_webhook.py, _try_process_payment_provider_tx.

    @route(_process_url, type='http', auth='public', methods=['POST'], csrf=False)
    def payos_process_transaction(self, reference, **post):
        """Khách vừa bấm Thanh toán (redirect_form POST vào đây) - gọi payOS tạo link+QR
        thật rồi chuyển giao dịch sang pending, sau đó về lại trang trạng thái chuẩn của
        Odoo (tự polling, xem addons/payment/static/src/interactions/post_processing.js).
        """
        tx_sudo = request.env['payment.transaction'].sudo().search([
            ('reference', '=', reference), ('provider_code', '=', 'payos'),
        ], limit=1)
        tx_sudo._payos_create_payment_link()
        return request.redirect('/payment/status')
