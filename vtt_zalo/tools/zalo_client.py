# -*- coding: utf-8 -*-
"""Gọi thẳng REST API của Zalo (ZNS + OAuth làm mới token) bằng "requests" (đã có sẵn
trong dependencies chuẩn của Odoo, không cần external_dependencies riêng như payos SDK) -
tập trung toàn bộ chỗ gọi API ngoài vào 1 nơi, giống quy ước tools/payos_client.py của
module vtt_payos.
"""

import re

import requests

ZNS_MESSAGE_URL = 'https://business.openapi.zalo.me/message/template'
OAUTH_REFRESH_URL = 'https://oauth.zaloapp.com/v4/oa/access_token'

_TIMEOUT = 15

_NON_DIGIT_RE = re.compile(r'\D+')


def normalize_phone(phone):
    """Chuẩn hoá số điện thoại VN về đúng định dạng Zalo yêu cầu (84xxxxxxxxx, chỉ toàn
    chữ số) - res.partner.phone thường lưu lẫn dấu +/./,/khoảng trắng/gạch ngang (VD
    "+84 987.654-321", "090 123 4567", "090,123,4567"...) tuỳ người nhập, không đúng định
    dạng Zalo cần ngay. Dùng chung cho cả gửi thủ công (zalo.send.zns.wizard) lẫn tự động
    (sale_order._auto_send_zalo_zns).

    Bỏ TOÀN BỘ ký tự không phải chữ số bằng regex (\\D+) thay vì liệt kê từng ký tự riêng
    lẻ (dấu +/./,/-/khoảng trắng...) - chắc chắn không sót ký tự lạ nào, kể cả dấu + (vốn
    không phải chữ số nên tự bị regex loại, không cần xử lý riêng).
    """
    digits = _NON_DIGIT_RE.sub('', phone or '')
    if digits.startswith('0'):
        digits = '84' + digits[1:]
    return digits


def refresh_access_token(app_id, secret_key, refresh_token):
    """Làm mới access_token bằng refresh_token đang có - Zalo LUÔN trả về CẢ access_token
    VÀ refresh_token MỚI trong 1 lần gọi (refresh_token cũ hết hiệu lực ngay sau đó), nên
    bên gọi PHẢI lưu đè lại cả 2 giá trị, không được giữ refresh_token cũ lại dùng lần sau.

    Trả về dict {access_token, refresh_token}. Ném lỗi nguyên xi (requests.HTTPError hoặc
    Exception với nội dung response) nếu Zalo từ chối - bên gọi tự quyết định xử lý.
    """
    resp = requests.post(
        OAUTH_REFRESH_URL,
        headers={
            'secret_key': secret_key,
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        data={
            'app_id': app_id,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
        },
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get('access_token'):
        raise Exception('Làm mới access_token thất bại: %s' % data)
    return {
        'access_token': data['access_token'],
        'refresh_token': data.get('refresh_token', refresh_token),
    }


def send_zns_message(access_token, phone, template_id, template_data, tracking_id=None):
    """Gửi 1 tin ZNS theo mẫu đã được Zalo duyệt trước (template_id). Trả nguyên response
    JSON từ Zalo (error=0 nghĩa là thành công, khác 0 kèm message giải thích lỗi) - CỐ
    TÌNH không tự raise ở đây khi error != 0, để bên gọi (model/wizard) tự quyết định hiển
    thị/log/retry, chỉ raise khi bản thân request lỗi (mất kết nối, HTTP không phải 200).
    """
    payload = {
        'phone': phone,
        'template_id': template_id,
        'template_data': template_data,
    }
    if tracking_id:
        payload['tracking_id'] = tracking_id

    resp = requests.post(
        ZNS_MESSAGE_URL,
        headers={
            'Content-Type': 'application/json',
            'access_token': access_token,
        },
        json=payload,
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()
