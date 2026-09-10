{
    'name': 'VTT Payment payOS',
    'version': '1.0',
    'author': 'Seroto',
    'summary': 'Tích hợp payOS như 1 phương thức thanh toán chuẩn (payment.provider) cho Shop/eCommerce',
    'description': """
Cho phép khách chọn payOS ngay tại bước thanh toán chuẩn của Odoo (payment.provider) khi mua
hàng trên Shop/eCommerce (website_sale) - hiển thị mã QR payOS TRỰC TIẾP trên trang
/payment/status (không chuyển hướng sang trang payOS lưu trữ), tái dùng cơ chế
polling/redirect có sẵn của module "payment" (không cần JS mới).

Khác với module vtt_payos (chỉ phục vụ wizard đăng ký khóa học tùy biến của
vtt_seroto_website, có model/webhook riêng), module này đi đúng theo khung
payment.provider/payment.transaction chuẩn của Odoo, tái dùng lại tools/payos_client.py của
vtt_payos để gọi SDK payOS (tránh lặp code gọi SDK ở 2 nơi). payOS chỉ cho khai báo 1 địa chỉ
webhook duy nhất cho cả tài khoản nên 2 module CHUNG 1 webhook (/payos/webhook của vtt_payos,
xem controllers/payos_webhook.py, _try_process_payment_provider_tx) - không đăng ký thêm URL
nào khác trên my.payos.vn. Cũng dùng CHUNG credentials (Client ID/API Key/Checksum Key) đã
cấu hình sẵn ở vtt_payos (menu payOS > Cấu hình) - module này KHÔNG có field cấu hình riêng
trên payment.provider, tránh nhập trùng 2 nơi/rủi ro lệch khóa.

BẮT BUỘC cài thêm trên server: pip install payos (xem external_dependencies).
    """,
    'depends': ['payment', 'vtt_payos'],
    'external_dependencies': {
        'python': ['payos'],
    },
    'data': [
        'views/payment_payos_templates.xml',
        'data/payment_method_data.xml',
        'data/payment_provider_data.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
