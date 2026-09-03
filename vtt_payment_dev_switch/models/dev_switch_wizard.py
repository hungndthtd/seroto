from odoo import api, fields, models

from .course_registration import DEV_SWITCH_PARAM

# Liệt kê tường minh (không suy luận từ module nào đang cài) - dropdown, không phải
# checkbox, để sau này thêm cổng thanh toán thật khác (VD MoMo, VNPay) chỉ cần thêm 1
# dòng vào đây, không phải đổi lại kiểu field (Boolean chỉ chịu được đúng 2 lựa chọn).
PAYMENT_PROVIDER_SELECTION = [
    ('payos', 'PayOS'),
    ('bank_mock', 'Giả lập (dev)'),
]


class PaymentDevSwitchWizard(models.TransientModel):
    """Công tắc chọn cổng thanh toán đang dùng cho luồng "Đăng ký khóa học" - CHỈ DÙNG
    ĐỂ DEV TEST. Sao y mẫu payos.config.wizard (vtt_payos/models/
    payos_config_wizard.py): wizard nhỏ độc lập lưu thẳng vào ir.config_parameter,
    CỐ TÌNH không kế thừa res.config.settings.
    """
    _name = 'seroto.payment.dev.switch.wizard'
    _description = 'Cổng thanh toán (dev)'

    payment_provider = fields.Selection(
        PAYMENT_PROVIDER_SELECTION, string='Cổng thanh toán', required=True, default='payos',
        help='Chỉ chọn "Giả lập" khi đang code/test - chọn lại "PayOS (thật)" trước khi cần test đúng luồng thanh toán thật.',
    )

    def _compute_display_name(self):
        # Wizard không có field "tên" nào - mặc định Odoo sẽ hiện placeholder kỹ thuật
        # kiểu "seroto.payment.dev.switch.wizard,NewId_xxx" trên breadcrumb (view mở
        # full trang, target=current). Cố định 1 tên dễ đọc thay vào đó.
        for rec in self:
            rec.display_name = 'Cổng thanh toán'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        current = self.env['ir.config_parameter'].sudo().get_param(DEV_SWITCH_PARAM)
        res['payment_provider'] = current if current == 'bank_mock' else 'payos'
        return res

    def action_save(self):
        self.ensure_one()
        self.env['ir.config_parameter'].sudo().set_param(DEV_SWITCH_PARAM, self.payment_provider)
        return {'type': 'ir.actions.act_window_close'}
