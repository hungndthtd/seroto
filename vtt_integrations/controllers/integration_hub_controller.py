# -*- coding: utf-8 -*-
"""Webhook công khai nhận báo cáo/lệnh từ các site khách hàng (module vtt_integrations_agent
cài ở NƠI KHÁC) - đúng pattern controller webhook đã dùng ở vtt_payos
(controllers/payos_webhook.py): type='http', auth='public', csrf=False, tự đọc/parse JSON
tay (không dùng type='jsonrpc' vì bên gọi là "requests" thuần, không phải RPC JS của Odoo).

Xác thực bằng API Key riêng từng site (field integration.website.api_key) - KHÔNG dùng
session/cookie vì đây là giao tiếp máy-với-máy, không có người dùng đăng nhập.
"""

import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class IntegrationHubController(http.Controller):

    def _get_website_or_none(self, api_key):
        if not api_key:
            return None
        return request.env['integration.website'].sudo().search([('api_key', '=', api_key)], limit=1)

    # =====================================================
    # Agent -> Hub: báo cáo kết quả 1 lần kiểm tra kết nối (gọi mỗi khi agent tự kiểm tra
    # xong, xem vtt_integrations_agent/models/integration_connector.py, _push_report_to_hub)
    # =====================================================
    @http.route('/integration_hub/report', type='http', auth='public', methods=['POST'], csrf=False)
    def report(self, **kwargs):
        try:
            data = json.loads(request.httprequest.get_data())
        except ValueError:
            return request.make_json_response({'error': 'Invalid JSON'}, status=400)

        website = self._get_website_or_none(data.get('api_key'))
        if not website:
            return request.make_json_response({'error': 'Invalid API key'}, status=403)

        provider_type = data.get('provider_type')
        if not provider_type:
            return request.make_json_response({'error': 'Missing provider_type'}, status=400)

        Connector = request.env['integration.connector'].sudo()
        connector = Connector.search([
            ('client_site_id', '=', website.id),
            ('provider_type', '=', provider_type),
        ], limit=1)

        if not connector:
            selection = dict(Connector.fields_get(['provider_type'])['provider_type']['selection'])
            connector = Connector.create({
                'name': '%s - %s' % (selection.get(provider_type, provider_type), website.name),
                'provider_type': provider_type,
                'client_site_id': website.id,
                'is_remote': True,
                'supports_refresh': bool(data.get('supports_refresh')),
            })

        if data.get('token_expires_at'):
            connector.token_expires_at = data['token_expires_at']

        connector._apply_check_result(bool(data.get('ok')), data.get('message'))

        return request.make_json_response({'ok': True})

    # =====================================================
    # Agent -> Hub: hỏi có Nhiệm vụ nào đang chờ thực thi cho site này không (poll định kỳ,
    # xem vtt_integrations_agent, _cron_poll_remote_tasks)
    # =====================================================
    @http.route('/integration_hub/pending_tasks', type='http', auth='public', methods=['GET'], csrf=False)
    def pending_tasks(self, api_key=None, **kwargs):
        website = self._get_website_or_none(api_key)
        if not website:
            return request.make_json_response({'error': 'Invalid API key'}, status=403)

        tasks = request.env['integration.remote.task'].sudo().search([
            ('client_site_id', '=', website.id), ('state', '=', 'pending'),
        ])
        return request.make_json_response({
            'tasks': [
                {'id': t.id, 'provider_type': t.connector_id.provider_type, 'action': t.action}
                for t in tasks
            ],
        })

    # =====================================================
    # Agent -> Hub: báo kết quả THỰC THI 1 Nhiệm vụ - đóng vòng lặp 2 chiều
    # =====================================================
    @http.route('/integration_hub/task_result', type='http', auth='public', methods=['POST'], csrf=False)
    def task_result(self, **kwargs):
        try:
            data = json.loads(request.httprequest.get_data())
        except ValueError:
            return request.make_json_response({'error': 'Invalid JSON'}, status=400)

        website = self._get_website_or_none(data.get('api_key'))
        if not website:
            return request.make_json_response({'error': 'Invalid API key'}, status=403)

        task = request.env['integration.remote.task'].sudo().browse(data.get('task_id'))
        if not task.exists() or task.client_site_id != website:
            return request.make_json_response({'error': 'Invalid task'}, status=404)

        ok = bool(data.get('ok'))
        task.write({
            'state': 'done' if ok else 'error',
            'result_message': data.get('message'),
        })
        if task.connector_id:
            task.connector_id._apply_check_result(ok, data.get('message'))

        return request.make_json_response({'ok': True})
