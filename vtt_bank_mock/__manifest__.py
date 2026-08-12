{
    'name': 'VTT Seroto Bank',
    'version': '1.0',
    'author': 'Seroto',
    'summary': 'Giả lập cổng thanh toán ngân hàng (dev/test) - dùng khi chưa có API ngân hàng thật',
    'description': """
Module DEV/TEST - đóng vai 1 cổng thanh toán ngân hàng để các module khác (vd
vtt_seroto_website) test luồng "quét mã -> thanh toán -> nhận webhook báo kết quả"
mà KHÔNG cần tài khoản/API thật từ ngân hàng.

Cách dùng: module gọi tạo 1 bản ghi bank.mock.transaction (amount, description,
notify_url, notify_secret), lấy về checkout_url để mở cho khách "thanh toán" (trang giả
lập tự dựng). Khi khách bấm "Xác nhận"/"Hủy" trên trang đó, module tự POST kết quả
(kèm chữ ký HMAC) tới đúng notify_url - đúng hình dạng 1 webhook ngân hàng/cổng thanh
toán thật sẽ gọi, để sau này thay bằng tích hợp thật không phải đổi lại phía nhận.

KHÔNG phải lớp trung gian vĩnh viễn - khi có API ngân hàng/cổng thanh toán thật, module
gọi nó (vd vtt_seroto_website) sẽ đổi sang gọi thẳng API thật thay vì module này, có thể
gỡ bỏ phụ thuộc vào module này sau đó.
    """,
    'depends': ['website'],
    'data': [
        'security/ir.model.access.csv',
        'views/bank_mock_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'vtt_bank_mock/static/src/js/bank_mock.js',
        ],
    },
    'installable': True,
    'application': False,
}
