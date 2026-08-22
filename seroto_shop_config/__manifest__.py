{
    'name': 'Seroto Shop Config',
    'version': '1.0',
    'author': 'Seroto',
    'summary': 'Chặn không cho đăng công khai sản phẩm Khóa học/Gieo hạt lên Shop',
    'description': """
Module CẦU NỐI - chỉ có ý nghĩa khi đã cài Shop (website_sale). Phụ thuộc thẳng vào
website_sale nên KHÔNG cài được nếu chưa có Shop (không có rủi ro cài nhầm/cài sớm).

Sản phẩm học phí (gắn với 1 academic.course) và sản phẩm "Gieo hạt" (seroto_education)
chỉ nên bán qua đúng luồng Phiếu đăng ký/Đơn hàng nội bộ - không nên xuất hiện công khai
trên Shop. Module này chặn ngay tại bước ghi dữ liệu: hễ ai bật cờ "Đăng lên Website"
cho 1 trong 2 loại sản phẩm trên (kể cả bấm hàng loạt) sẽ bị báo lỗi ngay, không âm thầm
lộ ra ngoài.
    """,
    'depends': ['website_sale', 'seroto_education'],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
