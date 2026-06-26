from odoo import http
from odoo.http import request


class CourseRegisterAPI(http.Controller):

    @http.route(
        "/course/register",
        type="http",
        auth="public",
        csrf=True,
        methods=["POST"]
    )
    def course_register(self, **kwargs):

        name = kwargs.get("name")
        email = kwargs.get("email")
        phone = kwargs.get("phone")
        course_id = kwargs.get("course_id")

        if not name or not email:
            return request.make_json_response({
                "success": False,
                "message": "Thiếu thông tin bắt buộc"
            })

        lead = request.env["crm.lead"].sudo().create({
            "name": f"Course Register: {course_id}",
            "contact_name": name,
            "email_from": email,
            "phone": phone,
            "description": f"Course: {course_id}",
        })

        return request.make_json_response({
            "success": True,
            "lead_id": lead.id
        })