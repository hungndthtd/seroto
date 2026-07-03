from odoo import http
from odoo.http import request
from odoo.tools import html2plaintext


class WebsiteCourse(http.Controller):

    def _format_class_date_range(self, klass):
        """Trả về 'dd/mm' hoặc 'dd/mm - dd/mm' (nếu có ngày kết thúc) cho 1 lớp học."""
        if not klass.date_start:
            return ""
        date_range = klass.date_start.strftime("%d/%m")
        if klass.date_end:
            date_range += " - " + klass.date_end.strftime("%d/%m")
        return date_range

    def _format_enrollment_label(self, course):
        """VD 'Đang mở đăng ký K47' = trạng thái khóa học + mã lớp gần nhất."""
        state_labels = dict(course._fields["state"].selection)
        label = state_labels.get(course.state, "")
        class_code = course.next_class_id.code or ""
        if class_code:
            label = (label + " " + class_code).strip()
        return label

    @http.route(
        "/seroto/course/snippet",
        type="http",
        auth="public",
        website=True,
    )
    def course_snippet(self):

        category = request.env["product.category"].sudo().search(
            [("name", "=", "Khóa học")],
            limit=1,
        )

        domain = [
            ("sale_ok", "=", True),
            ("active", "=", True),
        ]

        if category:
            domain.append(("categ_id", "=", category.id))

        products = request.env["product.template"].sudo().search(
            domain,
            limit=3,
            order="id desc",
        )

        return request.render(
            "seroto_form.course_items",
            {
                "products": products,
            }
        )

    # NOTE: route bổ sung cho snippet kéo thả "Course Card"
    # (views/snippets/s_course_card.xml + static/src/js/course_snippet.js).
    # JS gọi route này ở mỗi lần trang tải để lấy danh sách khóa học mới nhất,
    # tránh nội dung bị "đóng băng" sau khi snippet đã được lưu tĩnh vào trang.
    @http.route(
        "/seroto/course/list",
        type="jsonrpc",
        auth="public",
        website=True,
    )
    def course_list(self, audience_code=None):

        domain = [("active", "=", True)]
        # audience_code: mã kỹ thuật của seroto.course.audience (vd 'teacher', 'student'),
        # gắn trên section snippet qua data-audience-code, đọc lại bởi course_snippet.js.
        # Không truyền (None) = không lọc, dùng cho snippet "Khóa học nổi bật" mặc định.
        if audience_code:
            domain.append(("audience_ids.code", "=", audience_code))

        courses = request.env["seroto.course"].sudo().search(domain, limit=3)

        course_type_labels = dict(courses._fields["course_type"].selection)

        return [
            {
                "id": course.id,
                "name": course.name,
                "subtitle": course.subtitle or "",
                # 'draft' = "Đang chờ" (chưa mở đăng ký) - JS dùng để disable nút
                # "Đăng ký ngay" thay vì cho khách bấm đăng ký khóa học chưa mở.
                "registration_open": course.state != "draft",
                # description là field Html (nhập qua rich-text editor) - JS hiển thị
                # bằng textContent (an toàn XSS) nên phải chuyển sang plain text ở đây,
                # nếu không sẽ in thẳng các thẻ <div data-oe-version="..."> ra màn hình.
                "description": html2plaintext(course.description or ""),
                "teacher": course.teacher_id.name or "",
                "course_type_label": course_type_labels.get(course.course_type, ""),
                "tuition_fee": course.tuition_fee,
                "enrollment_label": self._format_enrollment_label(course),
                "next_class_date": self._format_class_date_range(course.next_class_id),
                "schedule_note": course.next_class_id.schedule_note or "",
                "registration_deadline": (
                    course.next_class_id.registration_deadline.strftime("%d/%m")
                    if course.next_class_id.registration_deadline
                    else ""
                ),
                "image_url": (
                    "/web/image/seroto.course/%s/image" % course.id
                    if course.image
                    else "/web/static/img/placeholder.png"
                ),
            }
            for course in courses
        ]