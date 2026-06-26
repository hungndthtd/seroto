# controllers/main.py

from odoo import http
from odoo.http import request

class CourseEventController(http.Controller):

    @http.route('/course/register', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    def course_register(self, **kwargs):
        return {
            "status": "ok",
            "message": "registered successfully",
            "data": kwargs
        }