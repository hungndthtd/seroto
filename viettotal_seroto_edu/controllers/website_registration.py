# -*- coding: utf-8 -*-
"""
controllers/website_registration.py

Endpoint layer (mỏng) cho luồng đăng ký website: WEBSITE → CRM Lead → edu.admission.
Toàn bộ business logic nằm ở services/registration_service.py — controller
chỉ nhận request, gọi service, trả response.

Các route:
  GET  /dang-ky               → Landing page khoá học
  POST /dang-ky/quick-submit  → Form rút gọn trên landing page, chỉ tạo CRM Lead
  GET  /dang-ky/form          → Form đăng ký đầy đủ (có thể lọc theo khoá)
  POST /dang-ky/form/submit   → Nhận form, tạo CRM Lead + edu.admission
  GET  /dang-ky/cam-on        → Trang cảm ơn sau khi đăng ký
  GET  /dang-ky/tra-cuu       → Tra cứu tình trạng hồ sơ (theo SĐT/email)
  POST /dang-ky/tra-cuu       → Xử lý tra cứu
"""

import logging

from odoo import http
from odoo.http import request

from ..services.registration_service import RegistrationService, RegistrationValidationError

_logger = logging.getLogger(__name__)


class EduWebsiteRegistration(http.Controller):

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Landing page – danh sách khoá học đang mở đăng ký
    # ─────────────────────────────────────────────────────────────────────────
    @http.route('/dang-ky', type='http', auth='public', website=True, sitemap=True)
    def landing_page(self, **kwargs):
        service = RegistrationService(request.env)
        values = {
            'courses': service.get_published_courses(),
            'page_title': 'Đăng ký học – Seroto Education',
        }
        return request.render('viettotal_seroto_edu.website_landing_page', values)

    # ─────────────────────────────────────────────────────────────────────────
    # 1b. Form rút gọn trên landing page – chỉ tạo CRM Lead (chưa tạo hồ sơ
    #     tuyển sinh đầy đủ, tư vấn viên sẽ chốt khoá + thông tin sau)
    # ─────────────────────────────────────────────────────────────────────────
    @http.route('/dang-ky/quick-submit', type='http', auth='public',
                website=True, methods=['POST'], csrf=True)
    def quick_register(self, **post):
        service = RegistrationService(request.env)
        try:
            name = service.quick_register(post)
        except RegistrationValidationError:
            return request.redirect('/dang-ky?quick_error=1')
        return request.redirect(f'/dang-ky/cam-on?name={name}')

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Form đăng ký đầy đủ
    # ─────────────────────────────────────────────────────────────────────────
    @http.route('/dang-ky/form', type='http', auth='public', website=True, sitemap=True)
    def registration_form(self, course_id=None, class_id=None, **kwargs):
        """Form đăng ký chi tiết theo PDF: thông tin cá nhân + mục tiêu + phụ huynh."""
        service = RegistrationService(request.env)
        selected_course, classes, selected_class = service.resolve_course_and_class(course_id, class_id)
        values = service.build_form_context({
            'classes': classes,
            'selected_course': selected_course,
            'selected_class': selected_class,
        })
        return request.render('viettotal_seroto_edu.website_registration_form', values)

    # ─────────────────────────────────────────────────────────────────────────
    # AJAX: lấy danh sách lớp khi chọn khoá học
    # ─────────────────────────────────────────────────────────────────────────
    @http.route('/dang-ky/get-classes', type='json', auth='public', website=True)
    def get_classes_by_course(self, course_id=None, **kwargs):
        service = RegistrationService(request.env)
        try:
            return {'classes': service.get_classes_payload(course_id)}
        except Exception as e:
            _logger.error('get_classes_by_course error: %s', e)
            return {'classes': []}

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Xử lý submit form
    # ─────────────────────────────────────────────────────────────────────────
    @http.route('/dang-ky/form/submit', type='http', auth='public',
                website=True, methods=['POST'], csrf=True)
    def submit_registration(self, **post):
        service = RegistrationService(request.env)
        try:
            admission, partner = service.register_full(post)
        except RegistrationValidationError as exc:
            values = service.build_form_context({'errors': exc.errors, 'form_data': post})
            return request.render('viettotal_seroto_edu.website_registration_form', values)
        except Exception as e:
            _logger.exception('submit_registration error: %s', e)
            values = service.build_form_context({
                'errors': ['Có lỗi xảy ra khi gửi đăng ký. Vui lòng thử lại hoặc liên hệ trực tiếp với chúng tôi.'],
                'form_data': post,
            })
            return request.render('viettotal_seroto_edu.website_registration_form', values)

        return request.redirect(f'/dang-ky/cam-on?ref={admission.name}&name={partner.name}')

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Trang cảm ơn
    # ─────────────────────────────────────────────────────────────────────────
    @http.route('/dang-ky/cam-on', type='http', auth='public', website=True, sitemap=False)
    def thank_you(self, ref=None, name=None, **kwargs):
        values = {
            'ref':        ref or '',
            'name':       name or 'bạn',
            'page_title': 'Đăng ký thành công',
        }
        return request.render('viettotal_seroto_edu.website_thank_you', values)

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Tra cứu tình trạng hồ sơ
    # ─────────────────────────────────────────────────────────────────────────
    @http.route('/dang-ky/tra-cuu', type='http', auth='public', website=True,
                sitemap=True, methods=['GET', 'POST'])
    def lookup(self, **post):
        service = RegistrationService(request.env)
        results = None
        searched = False
        keyword = ''

        if request.httprequest.method == 'POST':
            keyword = post.get('keyword', '').strip()
            searched = True
            if keyword:
                results = service.lookup(keyword)

        values = {
            'results':    results,
            'searched':   searched,
            'keyword':    keyword,
            'page_title': 'Tra cứu hồ sơ đăng ký',
        }
        return request.render('viettotal_seroto_edu.website_lookup', values)
