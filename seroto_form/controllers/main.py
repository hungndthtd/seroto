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
    # 3. LEAD: get or create (dedupe email + course)
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

            lead_vals = {
                "name": lead_name,
                "partner_id": partner.id,
                "email_from": email,
                "phone": post.get("phone"),
                "description": post.get("note"),
                "team_id": team.id if team else False,
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
    # 4. CONTROLLER ENTRY POINT
    # =====================================================
    @http.route(
        "/course/register",
        type="http",
        auth="public",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def course_register(self, **post):

        _logger.info("========== COURSE REGISTER ==========")
        _logger.info("POST: %s", post)

        partner = self._get_or_create_partner(post)

        lead = self._get_or_create_lead(post, partner)

        _logger.info("FINAL LEAD ID=%s", lead.id)

        return request.redirect("/")