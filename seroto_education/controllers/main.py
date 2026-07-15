# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import json

class SerotoCourseController(http.Controller):

    @http.route('/course/register', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    def register_course(self, **kwargs):
        # 1. Honeypot check (Option 3)
        if kwargs.get('website'):
            return {'success': False, 'message': 'Hệ thống phát hiện hành vi gửi dữ liệu tự động. Đăng ký bị từ chối!'}

        name = kwargs.get('name')
        email = kwargs.get('email')
        phone = kwargs.get('phone')
        course_id = kwargs.get('course_id')

        if not name or not phone or not course_id:
            return {'success': False, 'message': 'Thiếu thông tin bắt buộc!'}

        course = request.env['academic.course'].sudo().browse(int(course_id))
        if not course.exists():
            return {'success': False, 'message': 'Khóa học không tồn tại!'}

        # 2. IP Rate-limit Check (Option 2 - Method 1)
        ip_address = request.httprequest.headers.get('X-Forwarded-For', request.httprequest.remote_addr)
        if ip_address and ',' in ip_address:
            ip_address = ip_address.split(',')[0].strip()

        import datetime
        one_hour_ago = datetime.datetime.now() - datetime.timedelta(hours=1)
        ip_logs_count = request.env['academic.ip.log'].sudo().search_count([
            ('ip_address', '=', ip_address),
            ('timestamp', '>=', one_hour_ago)
        ])
        if ip_logs_count >= 3:
            return {
                'success': False,
                'message': 'Thiết bị hoặc đường truyền của bạn đã gửi quá nhiều yêu cầu đăng ký liên tiếp. Vui lòng thử lại sau 1 giờ!'
            }

        # 3. Duplicate check for same contact + course within last 15 minutes
        time_limit = datetime.datetime.now() - datetime.timedelta(minutes=15)
        domain = [
            ('course_id', '=', course.id),
            ('create_date', '>=', time_limit),
        ]
        if email:
            domain += ['|', ('phone', '=', phone), ('email_from', '=', email)]
        else:
            domain += [('phone', '=', phone)]

        existing = request.env['crm.lead'].sudo().search(domain, limit=1)
        if existing:
            return {
                'success': False, 
                'message': 'Yêu cầu đăng ký khóa học này của bạn đang được xử lý. Vui lòng không đăng ký liên tiếp!'
            }

        # Create CRM Lead
        lead_vals = {
            'name': f"[Đăng ký Web] - {name} - {course.name}",
            'contact_name': name,
            'email_from': email,
            'phone': phone,
            'course_id': course.id,
            'description': f"Học viên đăng ký qua form Website.\nKhóa học: {course.name}\nHọ tên: {name}\nSĐT: {phone}\nEmail: {email or 'Không cung cấp'}",
            'user_id': False, # Assign manually or via CRM rules
        }
        
        # Try to find or create customer contact if possible, or let CRM lead convert handle it
        lead = request.env['crm.lead'].sudo().create(lead_vals)

        # Log successful IP registration
        request.env['academic.ip.log'].sudo().create({
            'ip_address': ip_address
        })

        return {
            'success': True,
            'message': 'Đăng ký thành công! Đội ngũ Seroto sẽ liên hệ với bạn sớm nhất.'
        }

    # =====================================================
    # Nhận lead từ Google Apps Script (trigger onFormSubmit gắn vào Google Form) -
    # gọi server-to-server, không qua trình duyệt nên không cần CORS, nhưng phải tự
    # xác thực bằng api_key (system parameter) vì endpoint public trên internet.
    # =====================================================
    @http.route('/api/google_form/lead', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    def google_form_lead(self, **kwargs):
        expected_key = request.env['ir.config_parameter'].sudo().get_param(
            'seroto_education.google_form_api_key'
        )
        if not expected_key or kwargs.get('api_key') != expected_key:
            return {'success': False, 'message': 'Unauthorized'}

        response_id = (kwargs.get('response_id') or '').strip()
        name = (kwargs.get('name') or '').strip()
        phone = (kwargs.get('phone') or '').strip()
        email = (kwargs.get('email') or '').strip()
        course_text = (kwargs.get('course') or '').strip()

        if not name or not phone:
            return {'success': False, 'message': 'Thiếu tên hoặc số điện thoại'}

        # Idempotency: Apps Script có thể gọi lại cùng 1 response (lỗi mạng, chạy tay
        # lại script) - tránh tạo trùng lead cho cùng 1 response_id.
        if response_id:
            existing = request.env['crm.lead'].sudo().search(
                [('google_form_response_id', '=', response_id)], limit=1
            )
            if existing:
                return {'success': True, 'message': 'Đã xử lý trước đó', 'lead_id': existing.id}

        course = False
        if course_text:
            course = request.env['academic.course'].sudo().search([
                '|', ('code', '=', course_text), ('name', '=', course_text),
            ], limit=1)

        Partner = request.env['res.partner'].sudo()
        partner = email and Partner.search([('email', '=', email)], limit=1)
        if not partner:
            partner = Partner.search([('phone', '=', phone)], limit=1)
        if not partner:
            partner = Partner.create({'name': name, 'email': email, 'phone': phone})

        source = request.env['utm.source'].sudo().search([('name', '=', 'Google Form')], limit=1)
        if not source:
            source = request.env['utm.source'].sudo().create({'name': 'Google Form'})

        lead_vals = {
            'name': f"[Google Form] {name} - {course.name if course else (course_text or 'Chưa rõ khóa học')}",
            'contact_name': name,
            'partner_id': partner.id,
            'email_from': email,
            'phone': phone,
            'course_id': course.id if course else False,
            'source_id': source.id,
            'google_form_response_id': response_id,
            'description': (
                f"Đăng ký qua Google Form.\nKhóa học (nhập tay trong form): {course_text or 'Không có'}"
            ),
        }
        lead = request.env['crm.lead'].sudo().create(lead_vals)

        return {'success': True, 'message': 'Đã tạo lead', 'lead_id': lead.id, 'partner_id': partner.id}
