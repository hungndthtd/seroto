# -*- coding: utf-8 -*-

import logging

from odoo import fields, models

from ..tools import zalo_client

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Chặn tự gửi TRÙNG cho sự kiện "Khi xác nhận thanh toán" - payment_state của hóa đơn
    # liên quan có thể đổi thành paid/in_payment nhiều lần trong cùng transaction (VD
    # write() được ORM gọi lại, hoặc thanh toán nhiều đợt) - chỉ tự gửi 1 LẦN/đơn hàng cho
    # sự kiện này (xem models/account_move.py, _auto_send_zalo_zns_on_payment).
    zalo_zns_payment_sent = fields.Boolean(
        string='Đã tự gửi ZNS thanh toán', default=False, copy=False,
    )

    # sale.order KHÔNG có sẵn field "lý do hủy" chuẩn trong Odoo Community (xem
    # zalo_zns_template.py, field_source='order_cancel_reason') - field này BỔ SUNG riêng
    # để lưu lại lý do Sale gõ ở wizard xác nhận hủy (xem action_cancel_with_zalo_prompt),
    # vừa để tra cứu trên form vừa để _resolve_template_data đọc được giá trị thật.
    cancel_reason = fields.Char(string='Lý do hủy đơn', copy=False)

    def action_open_zalo_send_zns_wizard(self):
        """Mở wizard "Gửi thử ZNS" kèm sẵn đơn hàng này (default_sale_order_id) - wizard tự
        resolve tham số theo field_source đã khai ở Mẫu tin (xem
        zalo.zns.template._resolve_template_data), không cần gõ tay JSON như gửi thử độc
        lập từ menu Zalo ZNS > Gửi thử ZNS.
        """
        self.ensure_one()
        return {
            'name': 'Gửi ZNS',
            'type': 'ir.actions.act_window',
            'res_model': 'zalo.send.zns.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_sale_order_id': self.id},
        }

    def action_cancel_with_zalo_prompt(self):
        """Thay cho nút "Hủy" gốc trên form (xem views/sale_order_views.xml, xpath đổi
        name="action_cancel" -> name này) - nếu KHÔNG có Mẫu tin nào đang kích hoạt cho sự
        kiện "Khi đơn hàng bị hủy", hủy y hệt hành vi gốc của Odoo (không có gì đổi khác,
        Sale chưa cấu hình Zalo cho sự kiện này thì không bị làm phiền thêm bước nào).

        Nếu CÓ mẫu tin, mở wizard hỏi "Lý do hủy đơn" (order_cancel_reason không tự resolve
        được từ sale.order - xem zalo_zns_template.py) TRƯỚC khi hủy thật - wizard tự gọi
        action_cancel() gốc + _auto_send_zalo_zns() sau khi xác nhận (xem
        wizard/zalo_sale_order_cancel_wizard.py).
        """
        template = self.env['zalo.zns.template'].sudo().search(
            [('auto_send_event', '=', 'sale_cancel'), ('active', '=', True)], limit=1,
        )
        if not template or len(self) != 1:
            return self.action_cancel()

        return {
            'name': 'Lý do hủy đơn',
            'type': 'ir.actions.act_window',
            'res_model': 'zalo.sale.order.cancel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_sale_order_id': self.id, 'default_template_id': template.id},
        }

    def _auto_send_zalo_zns(self, template, source='auto_payment'):
        """Tự gửi 1 tin ZNS theo "template" (đã xác định đúng auto_send_event ở nơi gọi,
        xem models/account_move.py cho sự kiện thanh toán, action_cancel_with_zalo_prompt/
        zalo.sale.order.cancel.wizard cho sự kiện hủy đơn) - dùng lại đúng logic resolve
        tham số + chuẩn hoá SĐT như wizard gửi tay (zalo.send.zns.wizard). "source" chỉ để
        ghi đúng nguồn gửi vào Nhật ký (zalo.zns.log).

        Lỗi ở bất kỳ bước nào (chưa cấu hình Access Token, thiếu SĐT, mất kết nối Zalo...)
        CHỈ log lại, KHÔNG được raise - hàm này có thể chạy kèm theo write() của
        account.move (sự kiện thanh toán), để lỗi thoát ra ngoài sẽ làm hỏng cả việc ghi
        nhận thanh toán/hóa đơn đang chạy, giống đúng quy ước _auto_process_payment (module
        vtt_seroto_website).
        """
        self.ensure_one()
        Log = self.env['zalo.zns.log']
        phone = ''
        template_data = None
        try:
            ICP = self.env['ir.config_parameter'].sudo()
            access_token = ICP.get_param('vtt_zalo.access_token')
            if not access_token:
                _logger.warning(
                    'Chưa cấu hình Access Token Zalo - bỏ qua tự gửi ZNS cho đơn %s', self.name)
                Log.create_log(
                    template=template, phone=phone, source=source, state='error',
                    sale_order=self, tracking_id=self.name,
                    response_message='Chưa cấu hình Access Token Zalo.',
                )
                return

            phone = zalo_client.normalize_phone(self.partner_id.phone)
            if not phone:
                _logger.warning(
                    'Đơn hàng %s không có SĐT khách hàng - bỏ qua tự gửi ZNS', self.name)
                Log.create_log(
                    template=template, phone=phone, source=source, state='error',
                    sale_order=self, tracking_id=self.name,
                    response_message='Đơn hàng không có SĐT khách hàng.',
                )
                return

            template_data = template._resolve_template_data(self)
            result = zalo_client.send_zns_message(
                access_token=access_token,
                phone=phone,
                template_id=template.template_id,
                template_data=template_data,
                tracking_id=self.name,
            )
            Log.create_log(
                template=template, phone=phone, source=source,
                state='success' if result.get('error') == 0 else 'error',
                sale_order=self, tracking_id=self.name, template_data=template_data,
                error_code=result.get('error'), response_message=result.get('message'),
            )
        except Exception as exc:
            _logger.exception(
                'Tự gửi ZNS thất bại cho đơn hàng %s (mẫu tin %s)', self.name, template.name)
            Log.create_log(
                template=template, phone=phone, source=source, state='error',
                sale_order=self, tracking_id=self.name, template_data=template_data,
                response_message=str(exc),
            )
