from odoo import http
from odoo.http import request

DEFAULT_LIMIT = 3


class AcademicCourseSnippetController(http.Controller):

    # Route RIÊNG cho snippet "Khóa học - Khu vực hiển thị"
    # (views/snippets/trang_chu/s_trang_chu_course_group.xml +
    # static/src/js/course_group_snippet.js) - đọc từ academic.course (module
    # seroto_education, model khóa học ĐANG DÙNG THẬT). CỐ TÌNH không dùng chung route
    # "/seroto/course/list" (định nghĩa trong seroto_form/controllers/website_snippet.py)
    # vì route đó đọc từ 'seroto.course' - model cũ, module seroto_form không còn dùng.
    @http.route(
        "/seroto/academic-course/list",
        type="jsonrpc", auth="public", website=True,
    )
    def academic_course_list(self, audience_code=None, **kwargs):
        # is_published LUÔN lọc, kể cả khi audience_code trống - "active" chỉ là cơ chế
        # lưu trữ/ẩn chung của Odoo, KHÔNG đồng nghĩa "đã sẵn sàng công khai trên
        # website" (khóa học mới tạo mặc định is_published=False, xem academic_course.py).
        domain = [("active", "=", True), ("is_published", "=", True)]
        # audience_code: mã kỹ thuật của academic.course.audience - Khu vực hiển thị
        # (vd 'teacher', 'school'), nhập ở panel Tùy chỉnh của snippet (data-audience-
        # code, xem s_course_group_option.xml) - không truyền (None) = không lọc theo
        # khu vực (nhưng vẫn lọc is_published ở trên).
        if audience_code:
            domain.append(("audience_ids.code", "=", audience_code))

        courses = request.env["academic.course"].sudo().search(domain, limit=DEFAULT_LIMIT)

        return [
            {
                "id": course.id,
                "name": course.name,
                "slogan": course.slogan or "",
                "format": course.format or "",
                "lecturer": course.lecturer or "",
                "batch_info": course.batch_info or "",
                "schedule_date": course.schedule_date or "",
                "schedule_time": course.schedule_time or "",
                "deadline_register": course.deadline_register or "",
                "is_registration_open": course.is_registration_open,
                "detail_url": course.detail_url or "",
                "image_url": (
                    "/web/image/academic.course/%s/image_256" % course.id
                    if course.image_1920
                    else "/web/static/img/placeholder.png"
                ),
            }
            for course in courses
        ]
