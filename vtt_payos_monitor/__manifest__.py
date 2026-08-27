{
    'name': 'VTT PayOS - Kết nối tích hợp',
    'version': '1.0',
    'author': 'Seroto',
    'summary': 'Cầu nối tự động: đăng ký payOS vào Dashboard giám sát Kết nối tích hợp',
    'description': """
Module cầu nối (auto_install) - KHÔNG cài tay được, tự động bật khi site cài CẢ vtt_payos
LẪN vtt_integrations_agent. Nếu site chỉ cần payOS mà không cần giám sát/báo cáo trạng
thái kết nối (Kết nối tích hợp), không cài vtt_integrations_agent thì module này cũng
không tồn tại - vtt_payos vẫn hoạt động đầy đủ, độc lập, không phụ thuộc gì vào đây.

Toàn bộ logic adapter (models/integration_connector.py) chuyển nguyên xi từ vtt_payos qua
đây - không đổi hành vi, chỉ đổi module nào sở hữu nó.
    """,
    'depends': ['vtt_payos', 'vtt_integrations_agent'],
    'auto_install': True,
    'data': [
        'data/integration_connector_data.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
