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
    'security/ir.model.access.csv',

    'data/ir_sequence_data.xml',
    # Modal đăng ký dùng chung, tách riêng khỏi views/templates.xml để không phụ
    # thuộc vào việc file đó có được bật hay không (snippet Course Card cần modal
    # này). LƯU Ý: nếu bật lại 'views/templates.xml' bên dưới, phải xoá template
    # id="course_register_modal" trong file đó trước, nếu không sẽ bị lỗi
    # "Duplicate XML ID" do 2 nơi cùng định nghĩa 1 external id.
    'views/course_register_modal.xml',
    # Bật lại snippet kéo thả "Course Card" (trước đây bị comment nên chưa hề
    # hiển thị trong Website Editor dù đã có file XML/JS).
    'views/snippets/s_course_card.xml',
    'views/snippets/snippets.xml',
    'views/seroto_course_views.xml',
    'views/seroto_student_views.xml',
    'views/sale_order_views.xml',
    'views/course_page.xml',
    'views/menu.xml',
  ],
  'assets': {
    'website.assets_wysiwyg': [
      'seroto_form/static/src/js/options.js',
      'seroto_form/static/src/js/course_snippet.js',
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