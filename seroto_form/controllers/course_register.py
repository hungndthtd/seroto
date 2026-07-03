import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class CourseRegister(http.Controller):

    # =====================================================
    # 1. PARTNER: get or create (dedupe by email)
    # =====================================================
    def _get_or_create_partner(self, post):

        email = (post.get("email") or "").strip()
        name = (post.get("name") or "").strip()

        partner = False

        if email:
            partner = request.env["res.partner"].sudo().search([
                ("email", "=", email)
            ], limit=1)

        if partner:
            _logger.info("Reusing partner ID=%s", partner.id)
            return partner

        partner = request.env["res.partner"].sudo().create({
            "name": name or email,
            "email": email,
            "phone": post.get("phone"),
        })

        _logger.info("Created partner ID=%s", partner.id)

        return partner

    # =====================================================
    # 2. TAG: course tag (create if not exists)
    # =====================================================
    def _get_or_create_tag(self, course):

        if not course:
            return False

        Tag = request.env["crm.tag"].sudo()

        tag = Tag.search([("name", "=", course)], limit=1)

        if not tag:
            tag = Tag.create({
                "name": course
            })
            _logger.info("Created tag ID=%s", tag.id)
        else:
            _logger.info("Reusing tag ID=%s", tag.id)

        return tag

    # =====================================================
    # 3. SOURCE: utm.source "Website" (create if not exists)
    # =====================================================
    def _get_or_create_source(self):

        Source = request.env["utm.source"].sudo()

        source = Source.search([("name", "=", "Website")], limit=1)

        if not source:
            source = Source.create({
                "name": "Website"
            })
            _logger.info("Created utm.source ID=%s", source.id)

        return source

    # =====================================================
    # 4. LEAD: get or create (dedupe email + course)
    # =====================================================
    def _get_or_create_lead(self, post, partner):

        course = (post.get("course") or "").strip()
        email = (post.get("email") or "").strip()

        lead_name = f"Đăng ký khóa học - {course}" if course else "Đăng ký khóa học"

        Lead = request.env["crm.lead"].sudo()

        domain = [
            ("email_from", "=", email),
            ("name", "=", lead_name),
        ]

        lead = Lead.search(domain, limit=1)

        if lead:
            _logger.info("Updating existing lead ID=%s", lead.id)

            lead.write({
                "phone": post.get("phone"),
                "description": post.get("note"),
                "partner_id": partner.id,
            })

        else:
            _logger.info("Creating new lead")

            team = request.env["crm.team"].sudo().search([], limit=1)
            source = self._get_or_create_source()

            lead_vals = {
                "name": lead_name,
                "partner_id": partner.id,
                "email_from": email,
                "phone": post.get("phone"),
                "description": post.get("note"),
                "expected_revenue": float(post.get("list_price") or 0),
                "team_id": team.id if team else False,
                "source_id": source.id,
            }

            lead = Lead.create(lead_vals)

        # attach tag AFTER create/update
        tag = self._get_or_create_tag(course)

        if tag:
            lead.write({
                "tag_ids": [(4, tag.id)]
            })

        return lead

    # =====================================================
    # 5. Thông tin khóa học để hiển thị modal "Đăng ký thành công"
    #    (static/src/js/register_modal.js đọc kết quả trả về của route bên dưới)
    # =====================================================
    def _format_class_date_range(self, klass):
        """Trả về 'dd/mm' hoặc 'dd/mm - dd/mm' (nếu có ngày kết thúc) cho 1 lớp học."""
        if not klass.date_start:
            return ""
        date_range = klass.date_start.strftime("%d/%m")
        if klass.date_end:
            date_range += " - " + klass.date_end.strftime("%d/%m")
        return date_range

    def _get_course_info(self, course_name):
        course = request.env["seroto.course"].sudo().search(
            [("name", "=", course_name)], limit=1
        )

        if not course:
            return False

        course_type_labels = dict(course._fields["course_type"].selection)

        return {
            "name": course.name,
            "image_url": (
                "/web/image/seroto.course/%s/image" % course.id
                if course.image
                else "/web/static/img/placeholder.png"
            ),
            "course_type_label": course_type_labels.get(course.course_type, ""),
            "teacher": course.teacher_id.name or "",
            "next_class_date": self._format_class_date_range(course.next_class_id),
            "schedule_note": course.next_class_id.schedule_note or "",
        }

    # =====================================================
    # 6. CONTROLLER ENTRY POINT
    #    type="jsonrpc": form được submit bằng AJAX (xem register_modal.js) để có thể
    #    hiển thị modal "Đăng ký thành công" ngay trên trang, không reload/redirect.
    # =====================================================
    @http.route(
        "/course/register",
        type="jsonrpc",
        auth="public",
        website=True,
    )
    def course_register(self, **post):

        _logger.info("========== COURSE REGISTER ==========")
        _logger.info("POST: %s", post)

        partner = self._get_or_create_partner(post)

        lead = self._get_or_create_lead(post, partner)

        _logger.info("FINAL LEAD ID=%s", lead.id)

        return {
            "success": True,
            "course": self._get_course_info((post.get("course") or "").strip()),
        }