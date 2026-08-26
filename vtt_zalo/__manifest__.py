{
    'name': 'VTT Zalo ZNS',
    'version': '1.0',
    'author': 'Seroto',
    'summary': 'Gửi thông báo qua Zalo ZNS (mẫu tin đã duyệt) - cấu hình kết nối + gửi thủ công',
    'description': """
Module gọi API ZNS (Zalo Notification Service) của Zalo để gửi tin thông báo giao dịch
theo mẫu đã được Zalo duyệt trước (VD "Xác nhận đơn hàng") - gửi được tới BẤT KỲ số điện
thoại nào, không cần người nhận đã follow Official Account, khác với tin nhắn OA thường.

Cấu hình App ID / Secret Key / Access Token / Refresh Token qua menu Zalo ZNS > Cấu hình
(lưu vào ir.config_parameter, chỉ nhóm Quản trị hệ thống mới xem/sửa được) - cùng quy ước
với module vtt_payos.

Access Token/Refresh Token ban đầu lấy từ luồng OAuth của Zalo (ngoài Odoo, qua OA admin
đăng nhập cấp quyền) rồi dán vào đây - module KHÔNG tự làm luồng OAuth lấy code lần đầu,
chỉ hỗ trợ làm mới (refresh) khi đã có refresh_token.

Menu "Gửi thử ZNS" dùng để kiểm tra kết nối + mẫu tin hoạt động đúng trước khi gắn gọi tự
động vào các luồng nghiệp vụ khác (VD module vtt_seroto_website khi phiếu đăng ký thanh
toán thành công).

Nút "Gửi ZNS" trên form Đơn bán hàng (Bán hàng > Đơn hàng) mở wizard trên kèm sẵn đơn hàng
đó - tự động resolve tham số theo "Trường thông tin" đã khai ở Mẫu tin (Mã đơn hàng, SĐT/
Tên khách hàng, Tổng tiền, Ngày đặt hàng, thông tin hóa đơn liên quan...), không cần gõ tay
JSON như gửi thử độc lập.

Mẫu tin có "Sự kiện gửi tin tự động" = "Khi xác nhận thanh toán" sẽ TỰ ĐỘNG gửi ngay khi
hóa đơn của đơn hàng chuyển trạng thái thanh toán "paid"/"in_payment" (hook account.move,
mỗi đơn hàng chỉ tự gửi 1 lần cho sự kiện này) - không cần bấm tay.

Mẫu tin có "Sự kiện gửi tin tự động" = "Khi đơn hàng bị hủy" cũng TỰ ĐỘNG gửi khi bấm nút
"Hủy" trên form Đơn bán hàng - mở wizard hỏi "Lý do hủy đơn" trước khi hủy thật (chưa cấu
hình mẫu tin nào cho sự kiện này thì nút "Hủy" hoạt động y hệt mặc định của Odoo, không có
gì thay đổi). Sự kiện còn lại (Khi xác nhận đơn hàng) hiện vẫn CHƯA có trigger tự động.

Menu "Danh sách gửi tin" (Zalo ZNS > Danh sách gửi tin) ghi lại MỌI lần gửi (thủ công lẫn
tự động, thành công lẫn lỗi) kèm mẫu tin/SĐT/đơn hàng/phản hồi từ Zalo để giám sát - đồng
thời mỗi lần gửi cũng đăng 1 dòng vào chatter của Đơn hàng liên quan.
    """,
    'depends': ['base', 'sale', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/zalo_config_wizard_views.xml',
        'views/zalo_zns_template_views.xml',
        'views/zalo_zns_log_views.xml',
        'views/sale_order_views.xml',
        'wizard/zalo_send_zns_wizard_views.xml',
        'wizard/zalo_sale_order_cancel_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
