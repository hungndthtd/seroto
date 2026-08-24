# -*- coding: utf-8 -*-
# payment_id (Phiếu thu) chưa từng được liên kết cho các Phiếu đăng ký "Hoàn tất" do
# nhân viên tạo thủ công (Đơn hàng -> Hóa đơn -> Ghi nhận thanh toán ngoài luồng payOS) -
# backfill lại bằng cách tra đúng Phiếu thu (account.payment) đã đối soát với hóa đơn
# của Đơn hàng gắn với từng phiếu.

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    registrations = env['seroto.course.registration'].search([
        ('state', '=', 'completed'),
        ('payment_id', '=', False),
        ('sale_order_id', '!=', False),
    ])
    for reg in registrations:
        invoices = reg.sale_order_id.invoice_ids.filtered(
            lambda m: m.payment_state in ('paid', 'in_payment')
        )
        for invoice in invoices:
            payments = invoice._get_reconciled_payments()
            if payments:
                reg.payment_id = payments[0].id
                break
