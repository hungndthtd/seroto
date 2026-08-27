{
    'name': 'VTT Integration Agent',
    'version': '1.0',
    'author': 'Seroto',
    'summary': 'Động cơ giám sát kết nối token-based với dịch vụ ngoài - cài độc lập trên từng site, tuỳ chọn báo cáo về Hub trung tâm',
    'description': """
Module "động cơ" NHẸ để giám sát kết nối kiểu "token" giữa Odoo và dịch vụ ngoài (payOS,
Zalo ZNS, ...) - CÀI ĐƯỢC ĐỘC LẬP trên bất kỳ site nào (kể cả site khách hàng), KHÔNG phụ
thuộc module Hub trung tâm (vtt_integrations).

Định nghĩa model 'integration.connector' (dispatch _check_connection/_refresh_token theo
provider_type) + cron tự kiểm tra định kỳ + Dashboard xem cục bộ - y hệt cách vtt_integrations
đã hoạt động trước đây, chỉ khác: module này không biết gì về "nhiều website/khách hàng"
(đó là khái niệm riêng của Hub).

Nếu site này cấu hình URL + API Key của 1 Hub trung tâm (module vtt_integrations, cài ở nơi
khác) qua menu Cấu hình - mỗi lần kiểm tra xong sẽ TỰ ĐỘNG đẩy báo cáo (POST HTTP) lên Hub.
KHÔNG cấu hình gì thì module vẫn hoạt động ĐẦY ĐỦ như 1 Dashboard giám sát độc lập tại chỗ.

Không có cơ chế "đăng ký qua link" tại runtime - việc thêm 1 loại tích hợp mới LUÔN cần 1
module Odoo thật (kế thừa model qua _inherit + khai depends).
    """,
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/integration_connector_views.xml',
        'views/agent_config_wizard_views.xml',
        'data/ir_cron_data.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
