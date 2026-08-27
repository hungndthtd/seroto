# -*- coding: utf-8 -*-
"""Adapter kết nối vtt_payos vào Dashboard giám sát (vtt_integrations_agent) - xem
docstring models/integration_connector.py bên module đó để hiểu đúng quy ước override.

Chuyển nguyên xi từ vtt_payos/models/integration_connector.py - tách ra module cầu nối
riêng (auto_install) để vtt_payos có thể cài độc lập, không bắt buộc cài kèm
vtt_integrations_agent nữa (xem __manifest__.py module này).

payOS dùng bộ 3 khóa TĨNH (Client ID/API Key/Checksum Key, xem payos_config_wizard.py) -
KHÔNG có khái niệm token hết hạn/refresh như OAuth (Zalo) - supports_refresh luôn False,
_refresh_token() không cần override (dùng nguyên bản gốc báo "không hỗ trợ").
"""

from odoo import models, fields, _


class IntegrationConnector(models.Model):
    _inherit = 'integration.connector'

    provider_type = fields.Selection(
        selection_add=[('payos', 'payOS')],
        ondelete={'payos': 'cascade'},
    )

    def _check_connection(self):
        if self.provider_type != 'payos':
            return super()._check_connection()

        ICP = self.env['ir.config_parameter'].sudo()
        client_id = ICP.get_param('vtt_payos.client_id')
        api_key = ICP.get_param('vtt_payos.api_key')
        checksum_key = ICP.get_param('vtt_payos.checksum_key')

        if not (client_id and api_key and checksum_key):
            return False, _(
                'Chưa cấu hình đủ Client ID/API Key/Checksum Key - vào payOS > Cấu hình.'
            )

        # CHỈ kiểm tra ĐÃ CÓ cấu hình đầy đủ, KHÔNG tự tạo 1 link thanh toán thật chỉ để
        # "ping" (sẽ tạo rác trên payOS + có thể phát sinh phí) - tình trạng gọi API THẬT đã
        # thể hiện qua các bản ghi payos.transaction (Giao dịch payOS) mỗi khi có đơn hàng
        # thanh toán thật, phản ánh đúng thực tế hơn 1 lệnh kiểm tra giả lập ở đây.
        return True, _('Đã cấu hình đầy đủ Client ID/API Key/Checksum Key.')
