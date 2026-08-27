# -*- coding: utf-8 -*-
"""Hàng đợi lệnh điều khiển từ xa - hoàn tất vòng lặp 2 chiều với site khách hàng:
  1. Kỹ thuật bấm "Làm mới Token" cho 1 kết nối is_remote=True trên Dashboard Hub
     -> tạo 1 bản ghi 'pending' ở đây (xem integration_connector.py, action_refresh_token).
  2. Agent bên site khách (module vtt_integrations_agent, cron _cron_poll_remote_tasks) tự
     poll qua controllers/integration_hub_controller.py (route /integration_hub/pending_tasks),
     thấy có Nhiệm vụ 'pending' -> TỰ THỰC THI tại chỗ bằng đúng credential thật của họ.
  3. Agent báo kết quả ngược lại qua route /integration_hub/task_result -> cập nhật record
     này thành 'done'/'error'.

Hub KHÔNG BAO GIỜ tự gọi API thật hộ site khách - chỉ tạo/theo dõi lệnh, việc THỰC THI
LUÔN xảy ra tại chính site khách (nơi có credential thật).
"""

from odoo import fields, models


class IntegrationRemoteTask(models.Model):
    _name = 'integration.remote.task'
    _description = 'Nhiệm vụ điều khiển từ xa cho Kết nối tích hợp'
    _order = 'create_date desc'
    _rec_name = 'connector_id'

    # Tên field KHÔNG được là "website_id" - xem giải thích ở integration_connector.py
    # (module core "website" patch get_base_url() dựa vào đúng tên field này).
    client_site_id = fields.Many2one('integration.website', string='Website', required=True, ondelete='cascade')
    connector_id = fields.Many2one('integration.connector', string='Kết nối', required=True, ondelete='cascade')
    action = fields.Selection([
        ('refresh_token', 'Làm mới Token'),
    ], string='Hành động', required=True, default='refresh_token')
    state = fields.Selection([
        ('pending', 'Chờ thực thi'),
        ('done', 'Đã hoàn thành'),
        ('error', 'Lỗi'),
    ], string='Trạng thái', default='pending', required=True)
    result_message = fields.Char(string='Kết quả')
