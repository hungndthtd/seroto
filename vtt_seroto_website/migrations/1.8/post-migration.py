# -*- coding: utf-8 -*-
# Sửa lại các Phiếu đăng ký đã lỡ rơi vào tình trạng: state đã chuyển "Hoàn tất" (nghĩa
# là chắc chắn đã thanh toán - state chỉ chuyển "completed" qua đúng hook thanh toán ở
# account_move.py) nhưng payment_status vẫn còn "unpaid" (do trước đây hook đó bỏ sót
# field này) - thường gặp ở các phiếu Sale tạo tay cho khách liên hệ ngoài, thanh toán
# qua kênh không phải payOS.

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    registrations = env['seroto.course.registration'].search([
        ('state', '=', 'completed'),
        ('payment_status', '!=', 'paid'),
    ])
    if registrations:
        registrations.write({'payment_status': 'paid'})
