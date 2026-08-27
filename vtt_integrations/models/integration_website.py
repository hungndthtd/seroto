# -*- coding: utf-8 -*-
"""Danh sách Khách hàng/Website - CHUẨN BỊ cho hướng mở rộng sau này: Hub này sẽ giám sát
kết nối tích hợp của NHIỀU website/site khách hàng khác nhau (không chỉ site hiện tại),
không đợi lúc thật sự có nhiều site mới thêm field này (tránh phải migrate dữ liệu
integration.connector đã có sau này).
"""

import secrets

from odoo import fields, models


class IntegrationWebsite(models.Model):
    _name = 'integration.website'
    _description = 'Khách hàng/Website (site đang được giám sát tích hợp)'
    _order = 'name'

    name = fields.Char(string='Tên', required=True)
    url = fields.Char(string='Địa chỉ website', help='VD: https://seroto.edu.vn')
    partner_id = fields.Many2one('res.partner', string='Khách hàng')
    active = fields.Boolean(default=True)
    note = fields.Text(string='Ghi chú')

    # Dán vào ô "API Key" của module vtt_integrations_agent (menu Kết nối tích hợp > Cấu
    # hình) cài trên CHÍNH site khách hàng này - dùng để xác thực báo cáo webhook gửi về
    # (xem controllers/integration_hub_controller.py). Tự sinh ngẫu nhiên, KHÔNG cho sửa
    # tay (chỉ tạo mới qua action_regenerate_api_key, tránh gõ nhầm 1 chuỗi yếu).
    api_key = fields.Char(
        string='API Key', copy=False, readonly=True, groups='base.group_system',
        default=lambda self: secrets.token_urlsafe(32),
    )

    def action_regenerate_api_key(self):
        for rec in self:
            rec.api_key = secrets.token_urlsafe(32)

    connector_ids = fields.One2many('integration.connector', 'client_site_id', string='Kết nối tích hợp')
    connector_count = fields.Integer(compute='_compute_connector_count')

    def _compute_connector_count(self):
        for rec in self:
            rec.connector_count = len(rec.connector_ids)
