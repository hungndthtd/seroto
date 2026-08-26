# -*- coding: utf-8 -*-
"""Nhật ký gửi ZNS - lưu lại MỌI lần gửi (thủ công lẫn tự động, thành công lẫn lỗi) để
giám sát/tra cứu, thay vì chỉ hiện thoáng qua trong result_message của wizard (mất ngay
khi đóng form) hoặc log server (không ai vào xem). Đồng thời ghi 1 dòng vào chatter của
Đơn hàng liên quan (nếu có) để thấy ngay trên khung Hoạt động, khớp yêu cầu người dùng.
"""

import json
import logging
from html import escape

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class ZaloZnsLog(models.Model):
    _name = 'zalo.zns.log'
    _description = 'Nhật ký gửi ZNS'
    _order = 'create_date desc'
    _rec_name = 'phone'

    template_id = fields.Many2one('zalo.zns.template', string='Mẫu tin', ondelete='set null')
    sale_order_id = fields.Many2one('sale.order', string='Đơn hàng', ondelete='set null')
    phone = fields.Char(string='Số điện thoại')
    source = fields.Selection([
        ('manual_test', 'Gửi thử (không gắn đơn hàng)'),
        ('manual_order', 'Gửi tay từ Đơn hàng'),
        ('auto_payment', 'Tự động - Khi xác nhận thanh toán'),
        ('auto_cancel', 'Tự động - Khi đơn hàng bị hủy'),
    ], string='Nguồn gửi', required=True)
    tracking_id = fields.Char(string='Tracking ID')
    template_data = fields.Text(string='Tham số đã gửi (JSON)')
    template_data_html = fields.Html(
        string='Tham số đã gửi', compute='_compute_template_data_html', sanitize=False,
    )
    state = fields.Selection([
        ('success', 'Thành công'),
        ('error', 'Lỗi'),
    ], string='Trạng thái', required=True)
    error_code = fields.Char(string='Mã lỗi Zalo', help='"0" nghĩa là thành công theo quy ước của Zalo.')
    response_message = fields.Text(string='Phản hồi')
    user_id = fields.Many2one('res.users', string='Người gửi', default=lambda self: self.env.user)

    @api.depends('template_data')
    def _compute_template_data_html(self):
        """Dựng bảng Tên tham số / Nội dung tham số, thay vì hiện nguyên khối JSON khó đọc."""
        for log in self:
            try:
                data = json.loads(log.template_data or '{}')
            except ValueError:
                data = {}

            if not data:
                log.template_data_html = '<p class="text-muted">(không có tham số)</p>'
                continue

            rows_html = ''.join(
                '<tr><td><code>&lt;%s&gt;</code></td><td>%s</td></tr>' % (escape(key), escape(str(value)))
                for key, value in data.items()
            )

            log.template_data_html = (
                '<table class="table table-sm table-bordered mb-0">'
                '<thead><tr><th>Tên tham số</th><th>Nội dung tham số</th></tr></thead>'
                '<tbody>%s</tbody>'
                '</table>'
            ) % rows_html

    @api.model
    def create_log(self, template, phone, source, state, sale_order=None, tracking_id=None,
                    template_data=None, error_code=None, response_message=None):
        """Ghi 1 dòng nhật ký + đăng kèm 1 message vào chatter của sale_order (nếu có) -
        dùng chung cho cả zalo.send.zns.wizard.action_send (gửi tay) lẫn
        sale_order._auto_send_zalo_zns (gửi tự động), tránh lặp lại logic ghi log ở 2 nơi.

        TỰ NUỐT lỗi (chỉ log server, không raise) - hàm này được gọi từ cả luồng tự động
        chạy kèm account.move.write() (xem sale_order._auto_send_zalo_zns), bản thân việc
        GHI LOG không được phép làm hỏng luồng thanh toán/hóa đơn đang chạy, kể cả khi việc
        ghi log này có vấn đề (VD message_post lỗi vì lý do gì đó).
        """
        try:
            log = self.sudo().create({
                'template_id': template.id if template else False,
                'sale_order_id': sale_order.id if sale_order else False,
                'phone': phone,
                'source': source,
                'state': state,
                'tracking_id': tracking_id,
                'template_data': (
                    json.dumps(template_data, ensure_ascii=False, indent=2) if template_data else False
                ),
                'error_code': str(error_code) if error_code is not None else False,
                'response_message': response_message,
            })

            if sale_order:
                template_name = template.name if template else _('(không xác định)')
                if state == 'success':
                    body = _('Gửi ZNS thành công - Mẫu tin: %s, SĐT: %s') % (template_name, phone)
                else:
                    body = _('Gửi ZNS thất bại - Mẫu tin: %s, SĐT: %s. Lỗi: %s') % (
                        template_name, phone, response_message or _('(không rõ)'),
                    )
                sale_order.sudo().message_post(body=body)

            return log
        except Exception:
            _logger.exception('Không ghi được Nhật ký gửi ZNS (template=%s, phone=%s)',
                               template.name if template else None, phone)
            return self.browse()
