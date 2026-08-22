# -*- coding: utf-8 -*-
"""Bọc quanh SDK chính thức "payos" (pip install payos) - tập trung toàn bộ chỗ gọi SDK
vào 1 nơi, để models/controllers khác không cần tự import "payos" rải rác. Giữ nguyên
chữ ký hàm (client_id, api_key, checksum_key, ...) như thiết kế ban đầu, để
models/payos_transaction.py không phải đổi cách gọi dù bên trong đổi cách hiện thực.

CẦN CÀI: pip install payos (xem __manifest__.py, external_dependencies) - KHÔNG có sẵn
trong Odoo/pip requirements chuẩn, phải tự cài trên server.
"""

from payos import PayOS
from payos.types import CreatePaymentLinkRequest


def _get_client(client_id, api_key, checksum_key):
    return PayOS(client_id=client_id, api_key=api_key, checksum_key=checksum_key)


def create_payment_link(client_id, api_key, checksum_key, order_code, amount, description,
                         return_url, cancel_url):
    """Gọi payOS tạo 1 link thanh toán mới qua SDK chính thức (payment_requests.create).

    Trả về dict {checkout_url, qr_code, payment_link_id}. Ném lỗi nguyên xi từ SDK nếu
    payOS từ chối tạo link - bên gọi tự quyết định xử lý (log, báo lỗi người dùng...).
    """
    payment_request = CreatePaymentLinkRequest(
        order_code=order_code,
        amount=amount,
        description=description,
        cancel_url=cancel_url,
        return_url=return_url,
    )
    payment_link = _get_client(client_id, api_key, checksum_key).payment_requests.create(payment_request)
    return {
        'checkout_url': payment_link.checkout_url,
        # SDK chưa có tài liệu xác nhận rõ 2 field này - dùng getattr phòng trường hợp
        # tên khác/không tồn tại, tránh vỡ luôn cả việc tạo link chỉ vì thiếu QR.
        'qr_code': getattr(payment_link, 'qr_code', None),
        'payment_link_id': getattr(payment_link, 'payment_link_id', None),
    }


def verify_webhook(client_id, api_key, checksum_key, raw_body):
    """Xác thực + giải mã dữ liệu webhook qua SDK chính thức (webhooks.verify) - ném lỗi
    nếu không hợp lệ (chữ ký sai/payload hỏng), trả về đối tượng có .order_code nếu hợp lệ.
    """
    return _get_client(client_id, api_key, checksum_key).webhooks.verify(raw_body)
