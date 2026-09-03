import hashlib
import hmac
import json
import logging

from odoo import http
from odoo.http import request
from odoo.tools import consteq

from ..models.course_registration import DEV_SWITCH_PARAM

_logger = logging.getLogger(__name__)


class DevBankMockWebhookController(http.Controller):

    # Nhận webhook từ bank.mock.transaction._notify() (vtt_bank_mock) - CỐ TÌNH mô
    # phỏng đúng mức độ nghiêm ngặt của /payos/webhook (vtt_payos/controllers/
    # payos_webhook.py): tự tính lại chữ ký HMAC phía server bằng notify_secret lưu
    # trong DB - payment_status chỉ đổi khi chữ ký khớp, KHÔNG tin bất kỳ payload nào
    # chưa qua bước xác thực này. Sau khi chữ ký đã khớp, trường "status" trong payload
    # mới được tin (xem lý do ở dưới - không dùng transaction.status query lại).
    @http.route(
        '/seroto/course-registration/dev-bank-mock-webhook',
        type='http', auth='public', methods=['POST'], csrf=False,
    )
    def dev_bank_mock_webhook(self, **kwargs):
        # Chặn đầu tiên - dù request có tới được cũng không làm gì nếu công tắc đang tắt.
        if request.env['ir.config_parameter'].sudo().get_param(DEV_SWITCH_PARAM) != 'bank_mock':
            return request.make_json_response({'message': 'disabled'}, status=403)

        raw = request.httprequest.get_data()
        try:
            payload = json.loads(raw)
        except ValueError:
            return request.make_json_response({'message': 'invalid payload'}, status=400)

        transaction = request.env['bank.mock.transaction'].sudo().search(
            [('reference', '=', payload.get('reference'))], limit=1,
        )
        if not transaction:
            _logger.info(
                'Webhook dev bank-mock: không tìm thấy giao dịch reference=%s',
                payload.get('reference'),
            )
            return request.make_json_response({'message': 'not found'}, status=404)

        # Tự tính lại HMAC bằng notify_secret lưu trong DB (không phải giá trị client
        # gửi lên) rồi so sánh - transaction.notify_secret chỉ chính bản ghi này biết.
        expected_sig = hmac.new(transaction.notify_secret.encode(), raw, hashlib.sha256).hexdigest()
        given_sig = request.httprequest.headers.get('X-Bank-Mock-Signature', '')
        if not consteq(expected_sig, given_sig):
            _logger.warning(
                'Webhook dev bank-mock: chữ ký không khớp, reference=%s', payload.get('reference'),
            )
            return request.make_json_response({'message': 'invalid signature'}, status=400)

        # Đọc status từ payload ĐÃ XÁC THỰC chữ ký ở trên, KHÔNG query lại
        # transaction.status - action_confirm() (vtt_bank_mock) gọi _notify() đồng bộ
        # NGAY TRONG transaction đang ghi status='paid', chưa commit; request webhook
        # này mở cursor/connection MỚI nên theo cơ chế read-committed của Postgres sẽ
        # không thấy được thay đổi chưa commit đó - query lại transaction.status ở đây
        # luôn đọc ra giá trị CŨ ('pending'), gây lỗi 400 giả. payload.get('status')
        # an toàn tương đương vì đã được xác thực chữ ký HMAC ở trên - không ai giả
        # mạo được nếu không biết notify_secret.
        if payload.get('status') != 'paid':
            return request.make_json_response({'message': 'not paid'}, status=400)

        registration = request.env[transaction.related_res_model].sudo().browse(
            transaction.related_res_id).exists()
        if registration:
            registration._mark_paid_and_process()

        return request.make_json_response({'message': 'OK'})
