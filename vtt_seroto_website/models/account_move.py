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
        tự động chuyển Phiếu đăng ký sang "Hoàn tất".
        """
        for move in self:
            if move.payment_state in ('paid', 'in_payment'):
                sale_orders = move.line_ids.sale_line_ids.order_id
                registrations = self.env['seroto.course.registration'].sudo().search([
                    ('sale_order_id', 'in', sale_orders.ids),
                    ('state', '=', 'confirmed'),
                ])
                if registrations:
                    registrations.write({'state': 'completed'})
