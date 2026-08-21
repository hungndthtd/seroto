# -*- coding: utf-8 -*-
# student_relation trên seroto.course.registration được rút gọn từ 5 lựa chọn
# (self/child/parent/sibling/other) xuống còn 2 (self/other). Các phiếu cũ còn lưu
# child/parent/sibling sẽ làm SelectionField crash khi mở form (giá trị không còn
# nằm trong danh sách lựa chọn) - quy hết các giá trị cũ không phải "self" về "other",
# đúng ý nghĩa gốc là "đăng ký hộ người khác".


def migrate(cr, version):
    cr.execute("""
        UPDATE seroto_course_registration
        SET student_relation = 'other'
        WHERE student_relation IS NOT NULL
          AND student_relation NOT IN ('self', 'other')
    """)
