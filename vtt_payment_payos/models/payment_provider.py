# -*- coding: utf-8 -*-

from odoo import fields, models


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('payos', "payOS")], ondelete={'payos': 'set default'}
    )
    # CỐ TÌNH KHÔNG khai field Client ID/API Key/Checksum Key riêng ở đây (khác mẫu
    # payment_xendit) - dùng CHUNG đúng 1 nơi cấu hình đã có sẵn ở vtt_payos (menu payOS >
    # Cấu hình, lưu qua ir.config_parameter) vì cả 2 module cùng chung 1 tài khoản payOS
    # thật. Xem models/payment_transaction.py, _payos_create_payment_link - tự đọc qua
    # env['payos.transaction']._get_credentials(). Tránh phải nhập trùng 2 nơi/rủi ro lệch
    # khóa giữa 2 chỗ lưu.

    def _get_supported_currencies(self):
        """Override của `payment` - payOS chỉ xử lý VND."""
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'payos':
            supported_currencies = supported_currencies.filtered(lambda c: c.name == 'VND')
        return supported_currencies

    def _get_default_payment_method_codes(self):
        """Override của `payment` để trả về mã phương thức thanh toán mặc định."""
        self.ensure_one()
        if self.code != 'payos':
            return super()._get_default_payment_method_codes()
        return {'payos'}
