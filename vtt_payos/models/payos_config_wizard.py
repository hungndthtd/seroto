# -*- coding: utf-8 -*-

from odoo import api, fields, models

_KEYS = (
    ('client_id', 'vtt_payos.client_id', 'Client ID'),
    ('api_key', 'vtt_payos.api_key', 'API Key'),
    ('checksum_key', 'vtt_payos.checksum_key', 'Checksum Key'),
)


class PayOSConfigWizard(models.TransientModel):
    """Form cấu hình đơn giản cho 3 khóa payOS - CỐ TÌNH không kế thừa
    res.config.settings (tránh phải chèn vào màn hình Cài đặt chung vốn có cấu trúc
    phức tạp/hay đổi giữa các bản Odoo), chỉ là 1 wizard nhỏ độc lập lưu thẳng vào
    ir.config_parameter.
    """
    _name = 'payos.config.wizard'
    _description = 'Cấu hình payOS'

    client_id = fields.Char(string='Client ID')
    api_key = fields.Char(string='API Key')
    checksum_key = fields.Char(string='Checksum Key')
    current_status = fields.Char(string='Trạng thái hiện tại', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ICP = self.env['ir.config_parameter'].sudo()
        # CỐ TÌNH không nạp lại giá trị thật đã lưu vào form (field password="True" chỉ
        # che lúc hiển thị - giá trị vẫn nằm trong mã nguồn trang, xem được qua devtools
        # trình duyệt) - chỉ báo đã cấu hình hay chưa qua current_status. Để trống ô nào
        # lúc bấm Lưu nghĩa là GIỮ NGUYÊN giá trị cũ, không phải xóa - xem action_save().
        res['current_status'] = ' | '.join(
            '%s: %s' % (label, 'đã có' if ICP.get_param(param) else 'CHƯA có')
            for _field, param, label in _KEYS
        )
        return res

    def action_save(self):
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()
        for field_name, param, _label in _KEYS:
            value = getattr(self, field_name)
            if value:
                ICP.set_param(param, value)
        return {'type': 'ir.actions.act_window_close'}
