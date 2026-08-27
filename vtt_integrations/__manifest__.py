{
    'name': 'VTT Integration Hub',
    'version': '2.0',
    'author': 'Seroto',
    'summary': 'Giám sát tập trung các kết nối token-based với dịch vụ ngoài (payOS, Zalo ZNS, ...) - nhiều site khách hàng',
    'description': """
Hub giám sát TẬP TRUNG mọi kết nối kiểu "token" giữa Odoo và dịch vụ ngoài (payOS, Zalo
ZNS, và các tích hợp sau này) - dùng cho bộ phận Kỹ thuật xem 1 màn hình duy nhất: dịch vụ
nào đang ổn, dịch vụ nào token sắp hết hạn/đã lỗi, thay vì phải vào riêng từng module kiểm
tra.

CHỈ CÀI Ở SITE TRUNG TÂM của bộ phận Kỹ thuật - không cài trên site khách hàng (site khách
chỉ cần module vtt_integrations_agent, NHẸ hơn nhiều, xem module đó). Module này kế thừa
model 'integration.connector' đã định nghĩa ở vtt_integrations_agent (dispatch
_check_connection/_refresh_token theo provider_type), CHỈ thêm:
  - Model 'integration.website' (Danh sách khách hàng/site đang giám sát).
  - Field 'client_site_id'/'is_remote' trên integration.connector - phân biệt kết nối chạy tại
    chỗ (site này) với kết nối được BÁO CÁO từ 1 site khách hàng gửi về.
  - Webhook công khai (controllers/integration_hub_controller.py) nhận báo cáo từ Agent các
    site khách + hàng đợi Nhiệm vụ từ xa (integration.remote.task) để Kỹ thuật bấm "Làm mới
    Token" từ xa cho 1 site khách - site đó tự thực thi tại chỗ (đúng credential thật của
    họ) rồi báo kết quả ngược lại, KHÔNG BAO GIỜ Hub tự gọi API hộ site khách.
  - mail.thread/mail.activity.mixin - nhắc Kỹ thuật qua activity khi có kết nối lỗi/sắp hết
    hạn (áp dụng cho cả kết nối tại chỗ lẫn kết nối báo cáo từ xa).

Không có cơ chế "đăng ký qua link" tại runtime - việc thêm 1 loại tích hợp mới LUÔN cần 1
module Odoo thật (kế thừa model qua _inherit + khai depends), vì bản thân việc biết cách
gọi/xác thực 1 dịch vụ ngoài là logic lập trình, không phải cấu hình.
    """,
    'depends': ['base', 'mail', 'vtt_integrations_agent'],
    'data': [
        'security/ir.model.access.csv',
        'views/integration_connector_views.xml',
        'views/integration_website_views.xml',
        'views/integration_remote_task_views.xml',
        'data/integration_website_data.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
    'post_init_hook': 'assign_default_website',
}
