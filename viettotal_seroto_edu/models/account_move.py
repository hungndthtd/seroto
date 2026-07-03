# -*- coding: utf-8 -*-
"""
account_move.py
Khi hoá đơn (Invoice) của Sales Order gắn với edu.admission được thanh
toán đủ → tự động xác nhận thanh toán và tạo Học viên, không cần tư vấn
viên bấm tay action_enroll().
"""

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _invoice_paid_hook(self):
        super()._invoice_paid_hook()
        self._edu_check_admission_fully_paid()

    def _edu_check_admission_fully_paid(self):
        invoices = self.filtered(lambda m: m.move_type == 'out_invoice')
        if not invoices:
            return
        admissions = self.env['edu.admission'].sudo().search([
            ('sale_order_id.invoice_ids', 'in', invoices.ids),
            ('state', 'not in', ('enrolled', 'cancelled')),
        ])
        for admission in admissions:
            if admission.invoice_payment_state == 'paid':
                admission.action_confirm_payment()
                admission.action_enroll()
