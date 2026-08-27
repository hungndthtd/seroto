# -*- coding: utf-8 -*-

from odoo import api, fields, models

_KEYS = (
    ('hub_url', 'vtt_integrations_agent.hub_url', 'URL Hub trung tâm'),
    ('api_key', 'vtt_integrations_agent.api_key', 'API Key'),
)


class AgentConfigWizard(models.TransientModel):
    """Form cấu hình đơn giản: URL Hub trung tâm (module vtt_integrations, cài ở site
    KHÁC) + API Key riêng cho site này - CỐ TÌNH không kế thừa res.config.settings, chỉ là
    1 wizard nhỏ độc lập lưu thẳng vào ir.config_parameter, giống hệt quy ước
    payos.config.wizard/zalo.config.wizard.

    Để trống 2 ô này (mặc định) - module vẫn hoạt động ĐẦY ĐỦ như 1 Dashboard giám sát cục
    bộ độc lập, chỉ là không đẩy báo cáo đi đâu cả.
    """
    _name = 'agent.config.wizard'
    _description = 'Cấu hình đẩy báo cáo lên Hub trung tâm'

    hub_url = fields.Char(string='URL Hub trung tâm', help='VD: https://hub.seroto.vn')
    api_key = fields.Char(string='API Key')
    current_status = fields.Char(string='Trạng thái hiện tại', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ICP = self.env['ir.config_parameter'].sudo()
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
