# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..tools import zalo_client

# (field_name, ir.config_parameter key, nhãn, tên field trạng thái tương ứng) - field
# trạng thái hiện bằng icon trên view (xem views/zalo_config_wizard_views.xml) thay vì text
# như current_status cũ.
_KEYS = (
    ('app_id', 'vtt_zalo.app_id', 'App ID', 'app_id_status'),
    ('secret_key', 'vtt_zalo.secret_key', 'Secret Key', 'secret_key_status'),
    ('access_token', 'vtt_zalo.access_token', 'Access Token', 'access_token_status'),
    ('refresh_token', 'vtt_zalo.refresh_token', 'Refresh Token', 'refresh_token_status'),
)

# 'error' CHỈ phát sinh cho access_token_status/refresh_token_status khi action_refresh_token
# gọi Zalo thất bại (xem bên dưới) - app_id_status/secret_key_status chỉ có 'ok'/'missing' vì
# module không tự xác thực được 2 giá trị này (chỉ Zalo mới biết đúng/sai).
STATUS_SELECTION = [('ok', 'Đã có'), ('missing', 'Chưa có'), ('error', 'Lỗi')]


class ZaloConfigWizard(models.TransientModel):
    """Form cấu hình đơn giản cho kết nối Zalo OA (ZNS) - CỐ TÌNH không kế thừa
    res.config.settings, chỉ là 1 wizard nhỏ độc lập lưu thẳng vào ir.config_parameter,
    giống hệt quy ước của payos.config.wizard (module vtt_payos).

    access_token/refresh_token BAN ĐẦU lấy từ luồng OAuth của Zalo (ngoài Odoo, qua OA
    admin đăng nhập cấp quyền ở Zalo Developers) rồi dán tay vào đây - module này KHÔNG tự
    làm bước lấy "code" lần đầu. Sau đó dùng nút "Làm mới Access Token" bên dưới để tự
    refresh khi access_token hết hạn (không cần lặp lại OAuth từ đầu).
    """
    _name = 'zalo.config.wizard'
    _description = 'Cấu hình kết nối Zalo ZNS'

    app_id = fields.Char(string='App ID')
    secret_key = fields.Char(string='Secret Key')
    access_token = fields.Char(string='Access Token')
    refresh_token = fields.Char(string='Refresh Token')

    app_id_status = fields.Selection(STATUS_SELECTION, string='Trạng thái App ID', default='missing')
    secret_key_status = fields.Selection(STATUS_SELECTION, string='Trạng thái Secret Key', default='missing')
    access_token_status = fields.Selection(STATUS_SELECTION, string='Trạng thái Access Token', default='missing')
    refresh_token_status = fields.Selection(STATUS_SELECTION, string='Trạng thái Refresh Token', default='missing')

    status_message = fields.Char(string='Thông báo', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ICP = self.env['ir.config_parameter'].sudo()
        # CỐ TÌNH không nạp lại giá trị thật đã lưu vào form (giống payos.config.wizard) -
        # chỉ báo đã cấu hình hay chưa qua icon trạng thái. Để trống ô nào lúc bấm Lưu
        # nghĩa là GIỮ NGUYÊN giá trị cũ, không phải xóa - xem action_save().
        for _field, param, _label, status_field in _KEYS:
            res[status_field] = 'ok' if ICP.get_param(param) else 'missing'
        return res

    def action_save(self):
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()
        for field_name, param, _label, status_field in _KEYS:
            value = getattr(self, field_name)
            if value:
                ICP.set_param(param, value)
                self[status_field] = 'ok'
        return {'type': 'ir.actions.act_window_close'}

    @api.model
    def _do_refresh_token(self, app_id=None, secret_key=None, refresh_token=None):
        """Logic LÀM MỚI THẬT (gọi Zalo + lưu đè ir.config_parameter) - tách riêng khỏi
        action_refresh_token (nút bấm trên form) để module vtt_zalo_monitor (adapter kết
        nối vào Dashboard giám sát chung, chỉ có khi cài thêm vtt_integrations_agent) gọi
        lại được CHÍNH XÁC cùng 1 logic, không viết trùng.

        app_id/secret_key/refresh_token truyền vào CHỈ để ưu tiên giá trị đang gõ dở trên
        form (xem action_refresh_token) - không truyền thì tự đọc từ ir.config_parameter,
        đúng luồng vtt_zalo_monitor sẽ dùng.

        Trả về dict {ok: bool, message: str, expires_at: datetime|None} - KHÔNG raise khi
        gọi Zalo thất bại (chỉ raise khi thiếu hẳn App ID/Secret Key/Refresh Token, coi là
        lỗi cấu hình chứ không phải lỗi kết nối).
        """
        ICP = self.env['ir.config_parameter'].sudo()
        app_id = app_id or ICP.get_param('vtt_zalo.app_id')
        secret_key = secret_key or ICP.get_param('vtt_zalo.secret_key')
        refresh_token = refresh_token or ICP.get_param('vtt_zalo.refresh_token')

        if not (app_id and secret_key and refresh_token):
            raise UserError(_(
                'Cần có đủ App ID / Secret Key / Refresh Token (đã lưu trước đó hoặc vừa '
                'nhập trên form) mới làm mới được Access Token.'
            ))

        try:
            result = zalo_client.refresh_access_token(app_id, secret_key, refresh_token)
        except Exception as exc:
            return {'ok': False, 'message': _('Làm mới Access Token thất bại: %s') % exc, 'expires_at': None}

        ICP.set_param('vtt_zalo.access_token', result['access_token'])
        ICP.set_param('vtt_zalo.refresh_token', result['refresh_token'])

        expires_at = None
        if result.get('expires_in'):
            expires_at = fields.Datetime.now() + timedelta(seconds=result['expires_in'])

        return {'ok': True, 'message': _('Đã làm mới Access Token thành công.'), 'expires_at': expires_at}

    def action_refresh_token(self):
        """Làm mới access_token bằng refresh_token đang lưu (hoặc vừa nhập trên form nếu
        có) - dùng khi access_token cũ đã hết hạn, tránh phải lặp lại toàn bộ luồng OAuth.

        Thiếu App ID/Secret Key/Refresh Token là lỗi NHẬP LIỆU (raise UserError chặn luôn,
        xem _do_refresh_token). Lỗi GỌI API Zalo (mất mạng, token đã thu hồi...) thì KHÔNG
        raise - set icon 'error' + status_message rồi mở lại form, để người dùng thấy ngay
        lỗi ở đâu thay vì chỉ có 1 popup thoáng qua rồi mất dấu vết tương ứng field nào lỗi.
        """
        self.ensure_one()
        result = self._do_refresh_token(
            app_id=self.app_id, secret_key=self.secret_key, refresh_token=self.refresh_token,
        )

        if not result['ok']:
            self.access_token_status = 'error'
            self.refresh_token_status = 'error'
            self.status_message = result['message']
            return self._reopen()

        ICP = self.env['ir.config_parameter'].sudo()
        self.access_token = ICP.get_param('vtt_zalo.access_token')
        self.refresh_token = ICP.get_param('vtt_zalo.refresh_token')
        self.access_token_status = 'ok'
        self.refresh_token_status = 'ok'
        self.status_message = result['message']

        return self._reopen()

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
