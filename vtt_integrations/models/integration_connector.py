# -*- coding: utf-8 -*-
"""Mở rộng model 'integration.connector' (định nghĩa GỐC nằm ở module vtt_integrations_agent
- xem docstring ở đó để hiểu contract _check_connection/_refresh_token) - Hub trung tâm CHỈ
thêm 3 việc, không định nghĩa lại dispatch pattern:

  1. client_site_id - biết kết nối này thuộc site khách hàng nào (khái niệm CHỈ Hub mới có,
     agent không biết gì về "nhiều site").
  2. is_remote - phân biệt kết nối CHẠY TẠI CHỖ (site đang cài Hub này, y hệt trước đây)
     với kết nối được TẠO TỪ báo cáo webhook của 1 site khách gửi về (xem controllers/
     integration_hub_controller.py) - 2 loại này cần xử lý khác nhau khi bấm nút, vì Hub
     KHÔNG có credential thật của site khách để tự gọi API hộ được.
  3. mail.thread/mail.activity.mixin - nhắc bộ phận Kỹ thuật qua mail.activity khi có kết
     nối lỗi/sắp hết hạn (agent gốc không có UI theo dõi nhiều người dùng nên không cần
     mixin này).
"""

from odoo import fields, models, _
from odoo.exceptions import UserError


class IntegrationConnector(models.Model):
    _inherit = ['integration.connector', 'mail.thread', 'mail.activity.mixin']

    # KHÔNG được đặt tên "website_id" - module core "website" tự patch get_base_url() cho
    # MỌI model, hễ thấy field tên đúng "website_id" là coi nó trỏ tới model "website" (core,
    # có field "domain") - trùng tên vô tình làm crash AttributeError bất cứ khi nào
    # get_base_url() được gọi (VD mail.activity gửi link thông báo qua email/SMS).
    client_site_id = fields.Many2one('integration.website', string='Website', tracking=True)
    is_remote = fields.Boolean(
        string='Kết nối từ xa', default=False, readonly=True,
        help='True nếu bản ghi này được tạo từ báo cáo webhook của 1 site khách hàng gửi '
             'về (xem controllers/integration_hub_controller.py) - False cho kết nối chạy '
             'tại chỗ trên chính site đang cài Hub này.',
    )

    def action_check_connection(self):
        if any(self.mapped('is_remote')):
            raise UserError(_(
                'Không thể tự kiểm tra kết nối từ xa ngay tại Hub - kết nối này chỉ cập '
                'nhật qua báo cáo tự động (webhook) từ chính site khách hàng, đợi lần báo '
                'cáo định kỳ tiếp theo.'
            ))
        return super().action_check_connection()

    def action_refresh_token(self):
        remote = self.filtered('is_remote')
        local = self - remote

        if local:
            super(IntegrationConnector, local).action_refresh_token()

        for rec in remote:
            if not rec.supports_refresh:
                raise UserError(_('Loại tích hợp "%s" không hỗ trợ tự làm mới Token.') % rec.name)
            if not rec.client_site_id:
                raise UserError(_(
                    'Kết nối "%s" là kết nối từ xa nhưng chưa gán Website - không biết gửi '
                    'lệnh cho site nào.'
                ) % rec.name)
            # KHÔNG tự gọi _refresh_token() ở đây - Hub không có credential thật của site
            # khách. Tạo 1 Nhiệm vụ chờ - agent bên site khách tự poll về, thực thi tại chỗ
            # bằng đúng credential của họ, rồi báo kết quả ngược lại (xem
            # controllers/integration_hub_controller.py, models/integration_remote_task.py).
            self.env['integration.remote.task'].create({
                'client_site_id': rec.client_site_id.id,
                'connector_id': rec.id,
                'action': 'refresh_token',
                'state': 'pending',
            })

    def _apply_check_result(self, ok, message):
        super()._apply_check_result(ok, message)
        if self.status in ('error', 'warning'):
            self._notify_technical_team()

    def _notify_technical_team(self):
        """Nhắc bộ phận Kỹ thuật (nhóm base.group_system) qua mail.activity - CHỈ tạo nếu
        chưa có activity CÙNG LOẠI đang mở cho đúng bản ghi này, tránh tạo trùng mỗi lần
        cron chạy lại trong lúc vẫn còn lỗi/sắp hết hạn.
        """
        self.ensure_one()
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not activity_type:
            return

        existing = self.env['mail.activity'].search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('activity_type_id', '=', activity_type.id),
        ], limit=1)
        if existing:
            return

        technical_users = self.env.ref('base.group_system').all_user_ids
        if not technical_users:
            return

        site_label = (' (%s)' % self.client_site_id.name) if self.client_site_id else ''
        summary = (
            _('Kết nối "%s"%s sắp hết hạn token') if self.status == 'warning'
            else _('Kết nối "%s"%s đang lỗi')
        ) % (self.name, site_label)

        self.activity_schedule(
            'mail.mail_activity_data_todo',
            summary=summary,
            note=self.status_message,
            user_id=technical_users[0].id,
        )
