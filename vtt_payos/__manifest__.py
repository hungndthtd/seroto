{
    'name': 'VTT PayOS',
    'version': '1.3',
    'author': 'Seroto',
    'summary': 'Tích hợp cổng thanh toán payOS thật (tạo link thanh toán, nhận webhook, đối soát)',
    'description': """
Module gọi API payOS thật để tạo link/QR thanh toán và nhận webhook báo kết quả - vai
trò tương đương module vtt_bank_mock (dev/test) nhưng dùng cho production, cùng chung
1 quy ước "related_res_model/related_res_id" để bất kỳ module nào (vd
vtt_seroto_website) cũng gọi được mà không cần khai phụ thuộc ngược.

Xác thực webhook (controllers/payos_webhook.py) dùng đúng SDK chính thức "payos" -
BẮT BUỘC cài thêm trên server: pip install payos (không nằm trong requirements chuẩn
của Odoo, phải tự cài).

Cấu hình Client ID / API Key / Checksum Key qua menu payOS > Cấu hình (lưu vào
ir.config_parameter, chỉ nhóm Quản trị hệ thống mới xem/sửa được).

KHÔNG phụ thuộc module giám sát nào - cài độc lập, tự cấu hình tay, hoạt động đầy đủ dù
không có Dashboard giám sát "Kết nối tích hợp". Nếu site có cài THÊM vtt_integrations_agent,
module cầu nối "vtt_payos_monitor" (auto_install) sẽ tự bật để đăng ký kết nối này vào
Dashboard đó - không cần làm gì thêm, cũng không bắt buộc.
    """,
    'depends': ['base'],
    'external_dependencies': {
        'python': ['payos'],
    },
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'views/payos_config_wizard_views.xml',
        'views/payos_transaction_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
