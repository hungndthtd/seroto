# -*- coding: utf-8 -*-
"""Wizard chặn trước bước "Hủy" đơn hàng khi có Mẫu tin ZNS kích hoạt cho sự kiện "Khi đơn
hàng bị hủy" (xem models/sale_order.py, action_cancel_with_zalo_prompt) - hỏi Sale 1 "Lý do
hủy đơn" (order_cancel_reason không có field nguồn sẵn trên sale.order, xem
models/zalo_zns_template.py) trước khi hủy thật + tự gửi ZNS.
"""

from odoo import fields, models


class ZaloSaleOrderCancelWizard(models.TransientModel):
    _name = 'zalo.sale.order.cancel.wizard'
    _description = 'Lý do hủy đơn (kèm tự gửi ZNS)'

    sale_order_id = fields.Many2one('sale.order', string='Đơn hàng', required=True)
    template_id = fields.Many2one('zalo.zns.template', string='Mẫu tin sẽ gửi', required=True)
    cancel_reason = fields.Char(string='Lý do hủy đơn')

    def action_confirm_cancel(self):
        """Hủy đơn hàng THẬT (gọi đúng action_cancel gốc của Odoo, không có gì khác), lưu
        lại lý do lên sale_order.cancel_reason RỒI MỚI gửi ZNS - _resolve_template_data cần
        đọc được giá trị này (field_source='order_cancel_reason').
        """
        self.ensure_one()
        order = self.sale_order_id
        order.action_cancel()
        order.cancel_reason = self.cancel_reason
        order._auto_send_zalo_zns(self.template_id, source='auto_cancel')
        return {'type': 'ir.actions.act_window_close'}
