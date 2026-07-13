{
  'name': 'Seroto Form',
  'version': '1.0',
  'author': 'Seroto',
  'depends': [
    'website',
    'website_crm',
    'crm',
    'mail',
    'product',
    'contacts',
    # Cần để thêm field "Học viên" vào form Báo giá (sale.order) - xem
    # models/sale_order.py + views/sale_order_views.xml.
    'sale'
  ],
  'data': [
    # Nhóm quyền theo chức vụ (Sale/Giáo viên/CS học viên/Quản lý đào tạo/Quản trị
    # viên) - PHẢI load trước ir.model.access.csv vì CSV tham chiếu tới các group này.
    'security/seroto_security.xml',
    'security/ir.model.access.csv',

    'data/ir_sequence_data.xml',
    # Modal đăng ký dùng chung - snippet Course Card (module vtt_seroto_website) và
    # trang landing khóa học đều cần modal này, nên giữ lại ở đây (module gốc chứa
    # model + luồng CRM) thay vì tách sang module website.
    'views/course_register_modal.xml',
    'views/seroto_course_views.xml',
    'views/seroto_student_views.xml',
    # Bước 1 "Chăm sóc học viên": Điểm danh + Tiến độ học / % hoàn thành.
    # Phải load SAU seroto_course_views.xml/seroto_student_views.xml vì kế thừa
    # (inherit_id) các view định nghĩa trong 2 file đó.
    'views/seroto_care_views.xml',
    'views/sale_order_views.xml',
    'views/course_page.xml',
    'views/menu.xml',
  ],
  'assets': {
    'web.assets_frontend': [
      'seroto_form/static/src/js/register_modal.js',
      'seroto_form/static/src/css/style.css',
    ]
  },
  'installable': True,
  'application': True,
}
