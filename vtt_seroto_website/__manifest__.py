{
  'name': 'VTT Seroto Website',
  'version': '1.18',
  'author': 'Seroto',
  'summary': 'Snippet kéo-thả và trang landing khóa học trên website',
  'depends': [
    'website',
    # Gửi email xác nhận đăng ký (models/course_registration.py dùng mail.mail trực
    # tiếp) - vốn đã có sẵn qua phụ thuộc bắc cầu website -> portal -> mail, khai báo
    # thẳng ở đây cho rõ ràng thay vì ngầm định.
    'mail',
    # Cổng thanh toán payOS thật - xem models/course_registration.py,
    # _create_payment_transaction() (gọi payos.transaction.create_for_record) và
    # _payos_on_paid() (payos.transaction gọi ngược lại quy ước này khi đã thanh toán).
    'vtt_payos',
    # Đọc academic.course (models/course_registration.py, _get_course_questions) +
    # đặt menu "Phiếu đăng ký" trong nhóm "Tuyển sinh & Vận hành" của app Đào tạo (views/
    # course_registration_views.xml, parent="seroto_education.menu_academic_group_operation")
    # - khai depends thật (không còn phụ thuộc ngầm) vì menuitem BẮT BUỘC module chứa
    # menu cha phải nạp trước, không giống việc tra model qua self.env lúc runtime.
    'seroto_education',
    # Diện "Voucher quà tặng" - validate/áp mã "Phiếu giảm giá" chuẩn Odoo (Sales > Chiết
    # khấu & Khách hàng thân thiết) vào học phí, xem models/course_registration.py
    # _validate_voucher_code(). LƯU Ý: vì "sale" đã có sẵn (qua seroto_education ->
    # sale_management -> sale), khai thêm module này sẽ tự kéo theo sale_loyalty
    # (auto_install khi cả sale lẫn loyalty cùng có mặt) - chỉ thêm field/tính năng coupon
    # vào sale.order, không ảnh hưởng gì luồng hiện tại, KHÔNG dùng tới model/luồng đó.
    'loyalty',
    # Snippet/trang landing đọc dữ liệu seroto.course + dùng chung modal đăng ký
    # (course_register_modal, register_modal.js) định nghĩa trong seroto_form.
    # 'seroto_form',
  ],
  'data': [
    'security/ir.model.access.csv',
    # Thêm nút "Tạo trang landing" vào form Khóa học (kế thừa view của seroto_form) -
    # xem models/seroto_course.py trong module này để biết lý do action này KHÔNG thể
    # nằm ở seroto_form (tránh phụ thuộc vòng tròn).
    # 'views/seroto_course_views.xml',
    'views/templates/svg_templates.xml',
    'views/website_layout_fonts.xml',
    # Modal đăng ký khóa học nhiều bước ("Đăng ký ngay" trong s_trang_chu_course.xml) +
    # "Phiếu đăng ký khóa học" - gắn vào website.layout nên nạp trước các snippet.
    'views/course_register_wizard.xml',
    # Email xác nhận đăng ký + trang xem phiếu qua link email (models/controllers
    # course_registration.py).
    'views/course_registration_slip_page.xml',
    # Backend: menu "Phiếu đăng ký" (cạnh "Đợt học" trong app Đào tạo) để xem/quản lý
    # các phiếu đăng ký khóa học từ website.
    'views/course_registration_views.xml',
    'wizard/course_registration_reject_wizard_views.xml',
    # Bật snippet kéo thả.
    'views/snippets/s_block.xml',
    'views/snippets/s_course_card.xml',
    'views/snippets/s_team.xml',
    'views/snippets/s_project.xml',
    # 'views/snippets/s_roadmap_timeline.xml',
    # 'views/snippets/s_trai_nghiem_eq_timeline.xml',
    # 'views/snippets/trang_chu/s_trang_chu_course.xml',
    'views/snippets/trang_chu/s_trang_chu_course_group.xml',
    'views/snippets/trang_chu/s_trang_chu_sponsor.xml',
    'views/snippets/trang_chu/s_trang_chu_finance.xml',
    'views/snippets/trang_chu/s_trang_chu_team.xml',
    'views/snippets/trang_chu/s_trang_chu_vision.xml',
    'views/snippets/trang_chu/s_trang_chu_mission.xml',
    'views/snippets/trang_chu/s_trang_chu_culture.xml',
    'views/snippets/trang_chu/s_trang_chu_project.xml',
    'views/snippets/trang_chu/s_trang_chu_footer.xml',
    'views/snippets/eq_5_phut/s_eq_5_phut_hero.xml',
    'views/snippets/eq_5_phut/s_eq_5_phut_about.xml',
    'views/snippets/eq_5_phut/s_eq_5_phut_toward.xml',
    'views/snippets/eq_5_phut/s_eq_5_phut_timeline.xml',
    'views/snippets/eq_5_phut/s_eq_5_phut_footer.xml',
    'views/snippets/trai_nghiem_eq/s_trai_nghiem_eq_hero.xml',
    'views/snippets/trai_nghiem_eq/s_trai_nghiem_eq_timeline.xml',
    'views/snippets/trai_nghiem_eq/s_trai_nghiem_eq_footer.xml',
    'views/snippets/thuc_hanh_eq/s_thuc_hanh_eq_hero.xml',
    'views/snippets/thuc_hanh_eq/s_thuc_hanh_eq_about.xml',
    'views/snippets/thuc_hanh_eq/s_thuc_hanh_eq_quote.xml',
    'views/snippets/thuc_hanh_eq/s_thuc_hanh_eq_count.xml',
    'views/snippets/thuc_hanh_eq/s_thuc_hanh_eq_target.xml',
    'views/snippets/thuc_hanh_eq/s_thuc_hanh_eq_toward.xml',
    'views/snippets/thuc_hanh_eq/s_thuc_hanh_eq_teacher.xml',
    'views/snippets/thuc_hanh_eq/s_thuc_hanh_eq_method.xml',
    'views/snippets/thuc_hanh_eq/s_thuc_hanh_eq_scholarship.xml',
    'views/snippets/thuc_hanh_eq/s_thuc_hanh_eq_register.xml',
    'views/snippets/thuc_hanh_eq/s_thuc_hanh_eq_contact.xml',
    'views/snippets/thuc_hanh_eq/s_thuc_hanh_eq_content.xml',
    'views/snippets/thuc_hanh_eq/s_thuc_hanh_eq_faq.xml',
    'views/snippets/thuc_hanh_eq/s_thuc_hanh_eq_banner.xml',
    'views/snippets/thuc_hanh_eq/s_thuc_hanh_eq_footer.xml',
    'views/snippets/eq_master/s_eq_master_hero.xml',
    'views/snippets/eq_master/s_eq_master_benefit.xml',
    'views/snippets/eq_master/s_eq_master_user.xml',
    'views/snippets/eq_master/s_eq_master_teacher.xml',
    'views/snippets/eq_master/s_eq_master_content.xml',
    'views/snippets/eq_master/s_eq_master_course.xml',
    'views/snippets/eq_master/s_eq_master_method.xml',
    'views/snippets/eq_master/s_eq_master_faq.xml',
    'views/snippets/eq_master/s_eq_master_register.xml',
    'views/snippets/cha_me_eq_con_eq/s_cha_me_eq_con_eq_hero.xml',
    'views/snippets/cha_me_eq_con_eq/s_cha_me_eq_con_eq_problem.xml',
    'views/snippets/cha_me_eq_con_eq/s_cha_me_eq_con_eq_introduce.xml',
    'views/snippets/cha_me_eq_con_eq/s_cha_me_eq_con_eq_benefit.xml',
    'views/snippets/cha_me_eq_con_eq/s_cha_me_eq_con_eq_timeline.xml',
    'views/snippets/cha_me_eq_con_eq/s_cha_me_eq_con_eq_teacher.xml',
    'views/snippets/cha_me_eq_con_eq/s_cha_me_eq_con_eq_fee.xml',
    'views/snippets/cha_me_eq_con_eq/s_cha_me_eq_con_eq_faq.xml',
    'views/snippets/cha_me_eq_con_eq/s_cha_me_eq_con_eq_video.xml',
    'views/snippets/cha_me_eq_con_eq/s_cha_me_eq_con_eq_toward.xml',
    'views/snippets/cha_me_eq_con_eq/s_cha_me_eq_con_eq_contact.xml',
    'views/snippets/cha_me_eq_con_eq/s_cha_me_eq_con_eq_method.xml',
    'views/snippets/cha_me_eq_con_eq/s_cha_me_eq_con_eq_guide.xml',
    'views/snippets/cha_me_eq_con_eq/s_cha_me_eq_con_eq_count.xml',
    'views/snippets/cha_me_eq_con_eq/s_cha_me_eq_con_eq_banner.xml',
    'views/snippets/cha_me_eq_con_eq/s_cha_me_eq_con_eq_share.xml',
    'views/snippets/cha_me_eq_con_eq/s_cha_me_eq_con_eq_footer.xml',
    'views/snippets/tri_tue_cam_xuc/s_tri_tue_cam_xuc_hero.xml',
    'views/snippets/tri_tue_cam_xuc/s_tri_tue_cam_xuc_reason.xml',
    'views/snippets/tri_tue_cam_xuc/s_tri_tue_cam_xuc_benefit.xml',
    'views/snippets/tri_tue_cam_xuc/s_tri_tue_cam_xuc_register.xml',
    'views/snippets/tri_tue_cam_xuc/s_tri_tue_cam_xuc_fee.xml',
    'views/snippets/tri_tue_cam_xuc/s_tri_tue_cam_xuc_method.xml',
    'views/snippets/tri_tue_cam_xuc/s_tri_tue_cam_xuc_faq.xml',
    'views/snippets/tri_tue_cam_xuc/s_tri_tue_cam_xuc_feel.xml',
    'views/snippets/tri_tue_cam_xuc/s_tri_tue_cam_xuc_toward.xml',
    'views/snippets/tri_tue_cam_xuc/s_tri_tue_cam_xuc_curriculum.xml',
    'views/snippets/tri_tue_cam_xuc/s_tri_tue_cam_xuc_tool.xml',
    'views/snippets/tri_tue_cam_xuc/s_tri_tue_cam_xuc_policy.xml',
    'views/snippets/tri_tue_cam_xuc/s_tri_tue_cam_xuc_teacher.xml',
    'views/snippets/tri_tue_cam_xuc/s_tri_tue_cam_xuc_banner.xml',
    'views/snippets/tri_tue_cam_xuc/s_tri_tue_cam_xuc_footer.xml',
    'views/snippets/lang_live/s_lang_live_header.xml',
    'views/snippets/lang_live/s_lang_live_hero.xml',
    'views/snippets/lang_live/s_lang_live_video.xml',
    'views/snippets/lang_live/s_lang_live_reason.xml',
    'views/snippets/lang_live/s_lang_live_about.xml',
    'views/snippets/lang_live/s_lang_live_activity.xml',
    'views/snippets/lang_live/s_lang_live_timeline.xml',
    'views/snippets/lang_live/s_lang_live_address.xml',
    'views/snippets/lang_live/s_lang_live_team.xml',
    'views/snippets/lang_live/s_lang_live_footer.xml',
    'views/snippets/mang_eq_ve_truong/s_mang_eq_ve_truong_hero.xml',
    'views/snippets/mang_eq_ve_truong/s_mang_eq_ve_truong_about.xml',
    'views/snippets/mang_eq_ve_truong/s_mang_eq_ve_truong_target.xml',
    'views/snippets/mang_eq_ve_truong/s_mang_eq_ve_truong_concentrate.xml',
    'views/snippets/mang_eq_ve_truong/s_mang_eq_ve_truong_reason.xml',
    'views/snippets/mang_eq_ve_truong/s_mang_eq_ve_truong_benefit.xml',
    'views/snippets/mang_eq_ve_truong/s_mang_eq_ve_truong_map.xml',
    'views/snippets/mang_eq_ve_truong/s_mang_eq_ve_truong_video.xml',
    'views/snippets/mang_eq_ve_truong/s_mang_eq_ve_truong_data.xml',
    'views/snippets/mang_eq_ve_truong/s_mang_eq_ve_truong_rule.xml',
    'views/snippets/mang_eq_ve_truong/s_mang_eq_ve_truong_activity.xml',
    'views/snippets/mang_eq_ve_truong/s_mang_eq_ve_truong_count.xml',
    'views/snippets/mang_eq_ve_truong/s_mang_eq_ve_truong_quote.xml',
    'views/snippets/mang_eq_ve_truong/s_mang_eq_ve_truong_footer.xml',
    'views/snippets/qua_tang/s_qua_tang_hero.xml',
    'views/snippets/qua_tang/s_qua_tang_about.xml',
    'views/snippets/qua_tang/s_qua_tang_quote.xml',
    'views/snippets/qua_tang/s_qua_tang_reason.xml',
    'views/snippets/qua_tang/s_qua_tang_footer.xml',
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
      'vtt_seroto_website/static/src/js/options.js',
      'vtt_seroto_website/static/src/js/course_snippet.js',
    ],
    # Bundle riêng cho panel "Tùy chỉnh" (Customize) của Website Builder - nơi Odoo
    # nạp các plugin Option (vd website/static/src/builder/**/*). Option "Căn chỉnh"
    # của snippet "Title - Tiêu đề" phải nằm ở đây mới được panel nhận diện.
    'website.website_builder_assets': [
      'vtt_seroto_website/static/src/js/s_title_special_option.js',
      'vtt_seroto_website/static/src/xml/s_title_special_option.xml',
      # Ô nhập "Mã khu vực hiển thị" cho snippet "Khóa học - Khu vực hiển thị" (panel Tùy chỉnh).
      'vtt_seroto_website/static/src/js/s_course_group_option.js',
      'vtt_seroto_website/static/src/xml/s_course_group_option.xml',
      # Biến bất kỳ nút/link nào thành nút mở modal đăng ký khóa học ngay trên panel Tùy
      # chỉnh - không cần sửa Code View (xem course_register_button_option.js).
      'vtt_seroto_website/static/src/js/course_register_button_option.js',
      'vtt_seroto_website/static/src/xml/course_register_button_option.xml',
    ],
    'web.assets_frontend': [
      'vtt_seroto_website/static/src/js/course_snippet.js',
      'vtt_seroto_website/static/src/js/course_group_snippet.js',
      'vtt_seroto_website/static/src/js/course_register_wizard.js',
      'vtt_seroto_website/static/src/scss/snippet.scss',
      'vtt_seroto_website/static/src/scss/course_register_wizard.scss',
      'vtt_seroto_website/static/src/scss/s_trang_chu.scss',
      'vtt_seroto_website/static/src/scss/s_cha_me_eq_con_eq.scss',
      'vtt_seroto_website/static/src/scss/s_eq_5_phut.scss',
      'vtt_seroto_website/static/src/scss/s_thuc_hanh_eq.scss',
      'vtt_seroto_website/static/src/scss/s_tri_tue_cam_xuc.scss',
      'vtt_seroto_website/static/src/scss/s_lang_live.scss',
      'vtt_seroto_website/static/src/scss/s_mang_eq_ve_truong.scss',
      'vtt_seroto_website/static/src/scss/s_qua_tang.scss',
    ],
    # Style riêng cho form backend "Phiếu đăng ký khóa học" (views/
    # course_registration_views.xml) - web.assets_backend (không phải assets_frontend)
    # vì đây là view quản trị, không phải trang website.
    'web.assets_backend': [
      'vtt_seroto_website/static/src/scss/course_registration_backend.scss',
    ],
  },
  'installable': True,
  'application': False,
}
