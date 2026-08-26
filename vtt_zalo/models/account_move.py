# -*- coding: utf-8 -*-
"""Hook 'Khi xác nhận thanh toán' (auto_send_event = 'payment_confirm') - bắt đúng thời
điểm payment_state của hóa đơn chuyển paid/in_payment, y hệt cách seroto_education/models/
account_move.py đang hook _sync_enrollments_on_payment (2 lần: qua compute VÀ qua write()
trực tiếp, vì payment_state có thể đổi qua 1 trong 2 đường tuỳ luồng tạo thanh toán).
"""

from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('amount_residual', 'move_type', 'state', 'company_id', 'reconciled_payment_ids.state')
    def _compute_payment_state(self):
        super()._compute_payment_state()
        self._auto_send_zalo_zns_on_payment()

    def write(self, vals):
        res = super().write(vals)
        if 'payment_state' in vals:
            self._auto_send_zalo_zns_on_payment()
        return res

    def _auto_send_zalo_zns_on_payment(self):
        # Chỉ lấy 1 mẫu tin đang kích hoạt cho sự kiện này - nếu cấu hình nhiều hơn 1, chỉ
        # mẫu đầu tiên tìm được được dùng (đủ cho nhu cầu hiện tại: 1 sự kiện = 1 mẫu tin).
        template = self.env['zalo.zns.template'].sudo().search(
            [('auto_send_event', '=', 'payment_confirm'), ('active', '=', True)], limit=1,
        )
        if not template:
            return

        for move in self:
            if move.payment_state not in ('paid', 'in_payment'):
                continue

            orders = move.line_ids.sale_line_ids.order_id.filtered(
                lambda o: not o.zalo_zns_payment_sent,
            )
            for order in orders:
                # Đánh dấu ĐÃ GỬI trước khi thật sự gọi Zalo - chặn gọi trùng nếu write()
                # bị gọi lại nhiều lần trong cùng transaction (VD nhiều dòng hóa đơn cùng 1
                # đơn hàng), không phụ thuộc việc gửi có thành công hay không.
                order.zalo_zns_payment_sent = True
                order._auto_send_zalo_zns(template, source='auto_payment')
