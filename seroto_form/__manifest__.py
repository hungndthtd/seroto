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
    # Modal đăng ký dùng chung, tách riêng khỏi views/templates.xml để không phụ
    # thuộc vào việc file đó có được bật hay không (snippet Course Card cần modal
    # này). LƯU Ý: nếu bật lại 'views/templates.xml' bên dưới, phải xoá template
    # id="course_register_modal" trong file đó trước, nếu không sẽ bị lỗi
    # "Duplicate XML ID" do 2 nơi cùng định nghĩa 1 external id.
    'views/course_register_modal.xml',
    'views/templates/svg_templates.xml',
    # Bật lại snippet kéo thả "Course Card" (trước đây bị comment nên chưa hề
    # hiển thị trong Website Editor dù đã có file XML/JS).
    'views/snippets/s_block.xml',
    'views/snippets/s_course_card.xml',
    'views/snippets/s_team.xml',
    'views/snippets/s_project.xml',
    'views/snippets/snippets.xml',
    # Trang MẪU (is_new_page_template=True) cho các trang landing khóa học - url=
    # /maukhoahoc. Tạo trang khóa học thật (K19, K13...) qua Website Editor > "+New
    # Page" > nhóm Custom > chọn mẫu này, KHÔNG viết thêm file page_*.xml nào nữa.
    # LƯU Ý: nội dung viết TRỰC TIẾP (inline), KHÔNG t-call sang view khác bên trong
    # #wrap - t-call kiểu đó làm Website Builder mất khả năng chỉnh sửa (kéo-thả lẫn
    # sửa text) toàn bộ #wrap, đã kiểm chứng thực tế khi dựng bản pilot đầu tiên.
    'views/pages/page_maukhoahoc.xml',
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
    'website.assets_wysiwyg': [
      'seroto_form/static/src/js/options.js',
      'seroto_form/static/src/js/course_snippet.js',
    ],
    # Bundle riêng cho panel "Tùy chỉnh" (Customize) của Website Builder - nơi Odoo
    # nạp các plugin Option (vd website/static/src/builder/**/*). Option "Căn chỉnh"
    # của snippet "Title - Tiêu đề" phải nằm ở đây mới được panel nhận diện.
    'website.website_builder_assets': [
      'seroto_form/static/src/js/s_title_special_option.js',
      'seroto_form/static/src/xml/s_title_special_option.xml',
    ],
    'web.assets_frontend': [
      'seroto_form/static/src/js/register_modal.js',
      'seroto_form/static/src/css/style.css',
      'seroto_form/static/src/js/course_snippet.js',
      'seroto_form/static/src/scss/snippet.scss',
    ]
  },
  'installable': True,
  'application': True,
}