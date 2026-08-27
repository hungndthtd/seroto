# -*- coding: utf-8 -*-
"""Model gốc CHUNG để giám sát 1 kết nối tích hợp bên ngoài (token-based) - module này
(vtt_integrations_agent) là "động cơ" NHẸ, KHÔNG biết gì về nhiều-site/Khách hàng (đó là
khái niệm của Hub trung tâm, module vtt_integrations) - CÀI ĐƯỢC ĐỘC LẬP trên site khách
hàng, không cần cài Hub ở đó.

Mỗi module tích hợp (vtt_payos, vtt_zalo...) tự:
  1. Thêm 'vtt_integrations_agent' vào depends.
  2. Kế thừa model này (_inherit), thêm 1 giá trị vào provider_type qua selection_add.
  3. Override _check_connection()/_refresh_token() với guard "if self.provider_type !=
     '<mã của mình>': return super()....()" - đúng pattern Odoo core đang dùng cho
     delivery.carrier/payment.provider (mỗi provider tự nhận diện đúng bản ghi của mình,
     nhường lại cho provider khác nếu không phải của mình).
  4. Ship 1 bản ghi DỮ LIỆU (data/*.xml, noupdate="1") đại diện chính nó.

Nếu site này CÓ cấu hình URL + API Key của 1 Hub trung tâm (xem agent.config.wizard), mỗi
lần kiểm tra xong sẽ TỰ ĐỘNG đẩy báo cáo lên Hub (_push_report_to_hub) - KHÔNG cấu hình gì
thì module này vẫn hoạt động ĐẦY ĐỦ như 1 Dashboard giám sát cục bộ độc lập, y hệt cách
vtt_integrations hoạt động trước đây.

KHÔNG có cách "đăng ký" nào khác qua UI/link - việc biết cách gọi/xác thực 1 dịch vụ ngoài
là logic lập trình thật, phải nằm trong 1 module đã cài.
"""

import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..tools import hub_client

_logger = logging.getLogger(__name__)

# Cảnh báo "Sắp hết hạn" khi token còn hiệu lực dưới ngần này giờ - áp dụng cho MỌI loại
# tích hợp có khai token_expires_at (loại không có khái niệm hết hạn, VD payOS dùng API Key
# tĩnh, cứ để trống field này thì không bao giờ rơi vào trạng thái "warning").
TOKEN_EXPIRING_SOON_HOURS = 24


class IntegrationConnector(models.Model):
    _name = 'integration.connector'
    _description = 'Kết nối tích hợp bên ngoài (token-based)'
    _order = 'name'

    name = fields.Char(required=True)
    provider_type = fields.Selection([], string='Loại tích hợp', required=True)
    active = fields.Boolean(default=True)

    # Khai True ở data record của module tích hợp nếu dịch vụ đó CÓ khái niệm refresh token
    # (VD Zalo OAuth) - False (mặc định) cho dịch vụ dùng API Key tĩnh không hết hạn (VD
    # payOS) - nút "Làm mới Token" tự ẩn khi False (xem view).
    supports_refresh = fields.Boolean(string='Hỗ trợ tự làm mới Token', default=False)

    status = fields.Selection([
        ('not_configured', 'Chưa cấu hình'),
        ('ok', 'Đã kết nối'),
        ('warning', 'Sắp hết hạn'),
        ('error', 'Lỗi'),
    ], string='Trạng thái', default='not_configured', readonly=True)
    status_message = fields.Char(string='Thông báo', readonly=True)
    last_check_date = fields.Datetime(string='Lần kiểm tra gần nhất', readonly=True)
    last_success_date = fields.Datetime(string='Lần thành công gần nhất', readonly=True)
    # Để trống nếu dịch vụ không có khái niệm hết hạn (VD payOS) - chỉ module tích hợp có
    # OAuth token (VD Zalo) mới tính và ghi vào field này trong _refresh_token()/_check_connection().
    token_expires_at = fields.Datetime(string='Token hết hạn lúc', readonly=True)

    log_ids = fields.One2many('integration.connector.log', 'connector_id', string='Nhật ký kiểm tra')
    log_count = fields.Integer(compute='_compute_log_count')

    def _compute_log_count(self):
        for rec in self:
            rec.log_count = len(rec.log_ids)

    # =====================================================
    # Điểm mở rộng cho module tích hợp - KHÔNG override 2 hàm public bên dưới
    # (action_check_connection/action_refresh_token), chỉ override 2 hàm private
    # _check_connection/_refresh_token với guard theo provider_type.
    # =====================================================
    def _check_connection(self):
        """Trả về (ok: bool, message: str). Bản gốc (không provider nào khớp) coi là lỗi -
        không nên xảy ra thực tế trừ khi thiếu module tích hợp tương ứng."""
        self.ensure_one()
        return False, _('Chưa có adapter nào xử lý loại tích hợp "%s" - thiếu module tích hợp tương ứng?') % (
            self.provider_type or _('(chưa chọn)')
        )

    def _refresh_token(self):
        """Trả về dict {ok, message, expires_at} - chỉ gọi khi supports_refresh=True."""
        self.ensure_one()
        return {
            'ok': False,
            'message': _('Chưa có adapter nào xử lý làm mới token cho loại tích hợp "%s".') % (
                self.provider_type or _('(chưa chọn)')
            ),
            'expires_at': None,
        }

    # =====================================================
    # Hành động chung - KHÔNG cần biết provider_type nào tồn tại
    # =====================================================
    def action_check_connection(self):
        for rec in self:
            try:
                ok, message = rec._check_connection()
            except Exception as exc:
                _logger.exception('Kiểm tra kết nối thất bại cho %s', rec.name)
                ok, message = False, str(exc)
            rec._apply_check_result(ok, message)

    def action_refresh_token(self):
        for rec in self:
            if not rec.supports_refresh:
                raise UserError(_('Loại tích hợp "%s" không hỗ trợ tự làm mới Token.') % rec.name)
            try:
                result = rec._refresh_token()
            except Exception as exc:
                _logger.exception('Làm mới token thất bại cho %s', rec.name)
                result = {'ok': False, 'message': str(exc), 'expires_at': None}

            if result.get('expires_at'):
                rec.token_expires_at = result['expires_at']
            rec._apply_check_result(result['ok'], result['message'])

    def _apply_check_result(self, ok, message):
        """Cập nhật trạng thái + ghi log + đẩy báo cáo lên Hub (nếu có cấu hình). Module
        Hub trung tâm (vtt_integrations) override thêm hàm này (gọi super() rồi làm thêm
        việc riêng, VD tạo activity nhắc Kỹ thuật) - KHÔNG cần sửa file này khi mở rộng.
        """
        self.ensure_one()
        self.last_check_date = fields.Datetime.now()
        self.status_message = message

        if ok:
            self.last_success_date = fields.Datetime.now()
            self.status = 'warning' if self._is_token_expiring_soon() else 'ok'
        else:
            self.status = 'error'

        self.env['integration.connector.log'].create_log(self, ok, message)
        self._push_report_to_hub(ok, message)

    def _is_token_expiring_soon(self):
        self.ensure_one()
        if not self.token_expires_at:
            return False
        delta = self.token_expires_at - fields.Datetime.now()
        return delta.total_seconds() < TOKEN_EXPIRING_SOON_HOURS * 3600

    def _push_report_to_hub(self, ok, message):
        """Đẩy kết quả kiểm tra lên Hub trung tâm (nếu đã cấu hình URL + API Key qua menu
        Cấu hình) - TỰ NUỐT lỗi hoàn toàn (mất mạng, Hub tắt, sai API key...), không được
        làm hỏng luồng kiểm tra cục bộ đang chạy. Không cấu hình gì thì bỏ qua êm, module
        vẫn hoạt động đầy đủ như 1 Dashboard giám sát độc lập tại chỗ.
        """
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()
        hub_url = ICP.get_param('vtt_integrations_agent.hub_url')
        api_key = ICP.get_param('vtt_integrations_agent.api_key')
        if not (hub_url and api_key):
            return
        try:
            hub_client.push_report(hub_url, api_key, {
                'provider_type': self.provider_type,
                'ok': ok,
                'message': message,
                'token_expires_at': (
                    fields.Datetime.to_string(self.token_expires_at) if self.token_expires_at else None
                ),
            })
        except Exception:
            _logger.exception('Không đẩy được báo cáo kết nối "%s" lên Hub trung tâm', self.name)

    @api.model
    def _cron_check_all_connections(self):
        self.search([]).action_check_connection()

    @api.model
    def _cron_poll_remote_tasks(self):
        """Hoàn tất vòng lặp 2 chiều với Hub trung tâm (nếu có cấu hình): Hub tạo Nhiệm vụ
        (VD Kỹ thuật bấm "Làm mới Token" từ xa cho site này) -> site này TỰ THỰC THI tại
        chỗ (đúng _refresh_token() cục bộ, dùng credential THẬT của site này) -> báo kết
        quả ngược lại Hub. Không cấu hình Hub thì bỏ qua êm, không ảnh hưởng gì.
        """
        ICP = self.env['ir.config_parameter'].sudo()
        hub_url = ICP.get_param('vtt_integrations_agent.hub_url')
        api_key = ICP.get_param('vtt_integrations_agent.api_key')
        if not (hub_url and api_key):
            return

        try:
            tasks = hub_client.get_pending_tasks(hub_url, api_key)
        except Exception:
            _logger.exception('Không lấy được danh sách Nhiệm vụ từ xa từ Hub trung tâm')
            return

        for task in tasks:
            connector = self.search([('provider_type', '=', task.get('provider_type'))], limit=1)
            if not connector:
                ok, message = False, _('Site này không có kết nối loại "%s"') % task.get('provider_type')
            elif task.get('action') == 'refresh_token':
                try:
                    result = connector._refresh_token()
                    ok, message = result['ok'], result['message']
                    if result.get('expires_at'):
                        connector.token_expires_at = result['expires_at']
                except Exception as exc:
                    _logger.exception('Thực thi Nhiệm vụ từ xa #%s thất bại', task.get('id'))
                    ok, message = False, str(exc)
            else:
                ok, message = False, _('Hành động không hỗ trợ: %s') % task.get('action')

            if connector:
                connector._apply_check_result(ok, message)

            try:
                hub_client.report_task_result(hub_url, api_key, task['id'], ok, message)
            except Exception:
                _logger.exception('Không báo được kết quả Nhiệm vụ #%s về Hub trung tâm', task.get('id'))
