{
  'name': 'Seroto Website',
  'version': '1.0',
  'author': 'Seroto',
  'summary': '',
  'depends': [
    'website',
    # Snippet/trang landing đọc dữ liệu seroto.course + dùng chung modal đăng ký
    # (course_register_modal, register_modal.js) định nghĩa trong seroto_form.
    # 'seroto_form',
  ],
  'data': [
    # Thêm nút "Tạo trang landing" vào form Khóa học (kế thừa view của seroto_form) -
    # xem models/seroto_course.py trong module này để biết lý do action này KHÔNG thể
    # nằm ở seroto_form (tránh phụ thuộc vòng tròn).
    'views/seroto_course_views.xml',
    'views/templates/svg_templates.xml',
    # Bật snippet kéo thả.
    'views/snippets/s_block.xml',
    'views/snippets/s_course_card.xml',
    'views/snippets/s_team.xml',
    'views/snippets/s_project.xml',
    'views/snippets/s_roadmap_timeline.xml',
    'views/snippets/s_trai_nghiem_eq_timeline.xml',
    'views/snippets/snippets.xml',
    # Trang MẪU (is_new_page_template=True) cho các trang landing khóa học - url=
    # /maukhoahoc. Tạo trang khóa học thật (K19, K13...) qua Website Editor > "+New
    # Page" > nhóm Custom > chọn mẫu này, KHÔNG viết thêm file page_*.xml nào nữa.
    # LƯU Ý: nội dung viết TRỰC TIẾP (inline), KHÔNG t-call sang view khác bên trong
    # #wrap - t-call kiểu đó làm Website Builder mất khả năng chỉnh sửa (kéo-thả lẫn
    # sửa text) toàn bộ #wrap, đã kiểm chứng thực tế khi dựng bản pilot đầu tiên.
    'views/pages/page_maukhoahoc.xml',
  ],
  'assets': {
    'website.assets_wysiwyg': [
      'seroto_website/static/src/js/options.js',
      'seroto_website/static/src/js/course_snippet.js',
    ],
    # Bundle riêng cho panel "Tùy chỉnh" (Customize) của Website Builder - nơi Odoo
    # nạp các plugin Option (vd website/static/src/builder/**/*). Option "Căn chỉnh"
    # của snippet "Title - Tiêu đề" phải nằm ở đây mới được panel nhận diện.
    'website.website_builder_assets': [
      'seroto_website/static/src/js/s_title_special_option.js',
      'seroto_website/static/src/xml/s_title_special_option.xml',
    ],
    'web.assets_frontend': [
      'seroto_website/static/src/js/course_snippet.js',
      'seroto_website/static/src/scss/snippet.scss',
    ]
  },
  'installable': True,
  'application': False,
}
