# -*- coding: utf-8 -*-
"""Adapter kết nối vtt_zalo vào Dashboard giám sát (vtt_integrations_agent) - xem docstring
models/integration_connector.py bên module đó để hiểu đúng quy ước override.

Chuyển nguyên xi từ vtt_zalo/models/integration_connector.py - tách ra module cầu nối
riêng (auto_install) để vtt_zalo có thể cài độc lập, không bắt buộc cài kèm
vtt_integrations_agent nữa (xem __manifest__.py module này).
"""

from odoo import models, fields, _
from odoo.tools import format_datetime


class IntegrationConnector(models.Model):
    _inherit = 'integration.connector'

    provider_type = fields.Selection(
        selection_add=[('zalo_zns', 'Zalo ZNS')],
        ondelete={'zalo_zns': 'cascade'},
    )

    def _check_connection(self):
        if self.provider_type != 'zalo_zns':
            return super()._check_connection()

        ICP = self.env['ir.config_parameter'].sudo()
        app_id = ICP.get_param('vtt_zalo.app_id')
        secret_key = ICP.get_param('vtt_zalo.secret_key')
        access_token = ICP.get_param('vtt_zalo.access_token')

        if not (app_id and secret_key and access_token):
            return False, _(
                'Chưa cấu hình đủ App ID/Secret Key/Access Token - vào Zalo ZNS > Cấu hình.'
            )

        # Có ĐỦ giá trị KHÔNG có nghĩa access_token còn hiệu lực - Zalo có thể âm thầm thu
        # hồi/hết hạn access_token mà giá trị cũ vẫn còn nằm trong cấu hình (đã gặp thực tế:
        # "Kiểm tra kết nối" báo "Đã kết nối" trong khi gửi ZNS thật báo "Access token
        # invalid"). KHÔNG tự ping API ở đây (tốn phí/quota, không có endpoint an toàn) - mà
        # tham khảo lần GỬI THẬT gần nhất trong zalo.zns.log: nếu nó lỗi vì access_token,
        # coi kết nối đang lỗi luôn, không báo "Đã kết nối" sai sự thật.
        last_log = self.env['zalo.zns.log'].sudo().search([], order='create_date desc', limit=1)
        if last_log and last_log.state == 'error' and 'token' in (last_log.response_message or '').lower():
            # format_datetime TỰ chuyển từ UTC (lưu trong DB) sang múi giờ của user hiện tại
            # + định dạng theo ngôn ngữ - KHÔNG được nội suy thẳng last_log.create_date (naive
            # UTC) vào chuỗi bằng %s, sẽ lệch đúng bằng UTC offset (VD lệch 7 tiếng ở VN).
            when = format_datetime(self.env, last_log.create_date, dt_format='short')
            return False, _(
                'Access Token có thể đã hết hạn - lần gửi ZNS thật gần nhất (%s) báo lỗi: %s'
            ) % (when, last_log.response_message)

        return True, _('Đã cấu hình đầy đủ App ID/Secret Key/Access Token.')

    def _refresh_token(self):
        if self.provider_type != 'zalo_zns':
            return super()._refresh_token()

        # TÁI SỬ DỤNG đúng logic làm mới token của zalo.config.wizard (đọc/ghi
        # ir.config_parameter) - không viết trùng, đảm bảo "lấy token mới" và "cập nhật
        # đúng cấu hình mà send_zns_message() đọc" luôn là 1 hành động duy nhất.
        return self.env['zalo.config.wizard']._do_refresh_token()
