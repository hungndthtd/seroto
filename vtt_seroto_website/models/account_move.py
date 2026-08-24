# -*- coding: utf-8 -*-

from odoo import models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('amount_residual', 'move_type', 'state', 'company_id', 'reconciled_payment_ids.state')
    def _compute_payment_state(self):
        super()._compute_payment_state()
        self._sync_course_registrations_on_payment()

    def write(self, vals):
        res = super().write(vals)
        if 'payment_state' in vals:
            self._sync_course_registrations_on_payment()
        return res

    def _sync_course_registrations_on_payment(self):
        """Khi hóa đơn của đơn hàng gắn với 1 Phiếu đăng ký chuyển sang đã thanh toán
        (đồng thời academic_education.account_move đã tự ghi danh học viên vào lớp) ->
        tự động chuyển Phiếu đăng ký sang "Hoàn tất", đánh dấu "Đã thanh toán", VÀ liên
        kết luôn Phiếu thu (payment_id) - tra qua _get_reconciled_payments() của chính
        hóa đơn này.

        Áp dụng cho MỌI đường thanh toán, không riêng gì payOS - kể cả khi Sale tự tạo
        phiếu tay cho khách liên hệ ngoài (điện thoại/Zalo) và Kế toán tự ghi nhận thanh
        toán thủ công (tiền mặt, chuyển khoản qua kênh khác...) trên hóa đơn - trước đây
        chỉ luồng payOS mới tự cập nhật payment_status/payment_id (qua _payos_on_paid),
        luồng thủ công bị bỏ sót 2 field này, phiếu cứ treo mãi "Chưa thanh toán"/không
        có Phiếu thu dù đã chuyển "Hoàn tất" và học viên đã thực sự vào lớp.
        """
        for move in self:
            if move.payment_state not in ('paid', 'in_payment'):
                continue
            sale_orders = move.line_ids.sale_line_ids.order_id
            if not sale_orders:
                continue
            registrations = self.env['seroto.course.registration'].sudo().search([
                ('sale_order_id', 'in', sale_orders.ids),
                '|', ('state', '=', 'confirmed'), ('payment_id', '=', False),
            ])
            if not registrations:
                continue
            payments = move._get_reconciled_payments()
            for reg in registrations:
                vals = {}
                if reg.state == 'confirmed':
                    vals['state'] = 'completed'
                if reg.payment_status != 'paid':
                    vals['payment_status'] = 'paid'
                if not reg.payment_id and payments:
                    vals['payment_id'] = payments[0].id
                if vals:
                    reg.write(vals)
