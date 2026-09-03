{
    'name': 'VTT Payment Dev Switch',
    'version': '1.0',
    'author': 'Seroto',
    'summary': (
        'CHỈ DÙNG CHO DEV - công tắc bật/tắt cổng thanh toán giả lập (vtt_bank_mock) '
        'thay cho payOS thật khi test luồng đăng ký khóa học'
    ),
    'description': """
Module CHỈ DÀNH CHO MÔI TRƯỜNG DEV/TEST - TUYỆT ĐỐI KHÔNG CÀI TRÊN PRODUCTION.

Nối vtt_bank_mock (module giả lập ngân hàng có sẵn trong repo nhưng chưa module nào
gọi tới) vào luồng "Đăng ký khóa học" của vtt_seroto_website, qua 1 công tắc bật/tắt
(menu "Thanh toán (Dev)" > "Bật/tắt", chỉ nhóm Quản trị hệ thống thấy được), để nhân
viên developer có thể:
- Bật: pass nhanh qua bước "Thanh toán" bằng cổng giả lập, không cần chờ chuyển
  khoản thật qua payOS mỗi lần test các bước code tiếp theo (ghi danh, hóa đơn...).
- Tắt (mặc định khi mới cài): dùng lại payOS thật để test đúng luồng thanh toán thật
  song song, không xung đột.

KHÔNG sửa bất kỳ dòng nào trong vtt_seroto_website/vtt_payos/vtt_bank_mock - toàn bộ
chỉ dùng cơ chế kế thừa model (_inherit) chuẩn của Odoo để nối thêm hành vi, xem
models/course_registration.py.

An toàn: DB nào không cài module này thì toàn bộ field/route/wizard ở đây không tồn
tại trong registry - không có cách nào kích hoạt được dù có ai cố request tới. Khi đã
cài, còn cần bật tường minh qua công tắc (double-lock base.group_system, xem
views/dev_switch_wizard_views.xml) - payment_status chỉ đổi khi webhook giả lập tự
tính lại đúng chữ ký HMAC bằng secret sinh ngẫu nhiên phía server, không tin bất kỳ
trạng thái nào client tự khai (xem controllers/dev_bank_mock_webhook.py).
    """,
    'depends': ['vtt_seroto_website', 'vtt_bank_mock'],
    'data': [
        'security/ir.model.access.csv',
        'views/dev_switch_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
