# -*- coding: utf-8 -*-
"""Wizard gửi thử 1 tin ZNS thủ công - dùng để KIỂM TRA kết nối (Access Token) + mẫu tin
hoạt động đúng trước khi gắn lệnh gọi tự động vào các luồng nghiệp vụ khác (VD module
vtt_seroto_website khi phiếu đăng ký thanh toán thành công). Không tự raise khi Zalo trả
lỗi nghiệp vụ (error != 0) - hiện nguyên response vào result_message để người dùng tự đọc.
"""

import json
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..tools import zalo_client

_logger = logging.getLogger(__name__)


class ZaloSendZnsWizard(models.TransientModel):
    _name = 'zalo.send.zns.wizard'
    _description = 'Gửi thử ZNS thủ công'

    # Đặt sẵn qua context (default_sale_order_id) khi mở wizard từ nút "Gửi ZNS" trên form
    # Đơn hàng (xem models/sale_order.py, action_open_zalo_send_zns_wizard) - để trống khi
    # mở từ menu Zalo ZNS > Gửi thử ZNS (gửi thử không gắn đơn hàng nào, phải tự gõ JSON).
    sale_order_id = fields.Many2one('sale.order', string='Đơn hàng')
    template_id = fields.Many2one('zalo.zns.template', string='Mẫu tin', required=True)
    phone = fields.Char(
        string='Số điện thoại', required=True,
        help='Định dạng quốc tế không dấu +, VD: 84987654321',
    )
    template_data = fields.Text(
        string='Tham số (JSON)',
        help='Dạng {"order_code": "PDK8", "customer_name": "Chị Lan"} - đúng key đã khai ở Mẫu tin.',
    )
    tracking_id = fields.Char(string='Tracking ID', help='Tuỳ chọn - để đối soát ngược nếu cần.')
    result_message = fields.Text(string='Kết quả', readonly=True)

    # sale.order KHÔNG có field "lý do hủy" chuẩn (xem zalo_zns_template.py, ghi chú đầu
    # file) nên field_source='order_cancel_reason' KHÔNG tự resolve được - phải để Sale tự
    # gõ ở đây, chỉ hiện khi mẫu tin đang chọn thật sự có tham số dùng field_source này
    # (VD mẫu "Thông báo hủy đơn hàng"), xem has_cancel_reason_param + view.
    cancel_reason = fields.Char(string='Lý do hủy đơn')
    has_cancel_reason_param = fields.Boolean(compute='_compute_has_cancel_reason_param')

    @api.depends('template_id.param_ids.field_source')
    def _compute_has_cancel_reason_param(self):
        for wiz in self:
            wiz.has_cancel_reason_param = any(
                p.field_source == 'order_cancel_reason' for p in wiz.template_id.param_ids
            )

    @api.onchange('template_id', 'sale_order_id', 'cancel_reason')
    def _onchange_template_id(self):
        for wiz in self:
            if not wiz.template_id:
                wiz.template_data = False
                continue

            if wiz.sale_order_id:
                # Có đơn hàng (mở từ nút "Gửi ZNS" trên Sale Order) - TỰ resolve giá trị
                # thật theo field_source đã khai ở Mẫu tin (xem
                # zalo.zns.template._resolve_template_data), không cần gõ tay JSON nữa.
                data = wiz.template_id._resolve_template_data(wiz.sale_order_id)
                if not wiz.phone:
                    wiz.phone = zalo_client.normalize_phone(wiz.sale_order_id.partner_id.phone)
            else:
                # Gửi thử không gắn đơn hàng - chỉ dựng khung rỗng để tự gõ tay, KHÔNG
                # resolve được các field_source cần dữ liệu đơn hàng (order_name, v.v.).
                data = {p.key: '' for p in wiz.template_id.param_ids}

            # Ghi đè riêng cho order_cancel_reason bằng giá trị người dùng gõ ở ô "Lý do
            # hủy đơn" - _resolve_template_data không tự lấy được giá trị này (không có
            # field nguồn), dù có sale_order_id hay không.
            for p in wiz.template_id.param_ids:
                if p.field_source == 'order_cancel_reason':
                    data[p.key] = wiz.cancel_reason or ''

            wiz.template_data = json.dumps(data, ensure_ascii=False, indent=2)

    def action_send(self):
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()
        access_token = ICP.get_param('vtt_zalo.access_token')
        if not access_token:
            raise UserError(_(
                'Chưa cấu hình Access Token - vào menu Zalo ZNS > Cấu hình để nhập trước.'
            ))

        try:
            template_data = json.loads(self.template_data or '{}')
        except ValueError:
            raise UserError(_('Tham số (JSON) không hợp lệ - kiểm tra lại cú pháp JSON.'))

        # Zalo coi giá trị rỗng ("") là THIẾU tham số (lỗi error=-1122 "template data is
        # missing a parameter ...") - chặn sớm ở đây với thông báo tiếng Việt rõ ràng,
        # thay vì để round-trip qua Zalo rồi đọc mã lỗi thô.
        empty_keys = [k for k, v in template_data.items() if not str(v or '').strip()]
        if empty_keys:
            raise UserError(_(
                'Các tham số sau đang để trống - Zalo sẽ coi là THIẾU tham số, cần điền '
                'giá trị thật trước khi gửi: %s'
            ) % ', '.join(empty_keys))

        # Nguồn gửi để ghi vào Nhật ký (zalo.zns.log) - có sale_order_id nghĩa là mở từ nút
        # "Gửi ZNS" trên form Đơn hàng, không thì là gửi thử độc lập từ menu Zalo ZNS.
        source = 'manual_order' if self.sale_order_id else 'manual_test'
        Log = self.env['zalo.zns.log']

        try:
            result = zalo_client.send_zns_message(
                access_token=access_token,
                phone=self.phone,
                template_id=self.template_id.template_id,
                template_data=template_data,
                tracking_id=self.tracking_id,
            )
        except Exception as exc:
            _logger.exception('Gửi ZNS thủ công thất bại (template=%s, phone=%s)',
                               self.template_id.template_id, self.phone)
            self.result_message = 'Gọi API thất bại: %s' % exc
            Log.create_log(
                template=self.template_id, phone=self.phone, source=source, state='error',
                sale_order=self.sale_order_id, tracking_id=self.tracking_id,
                template_data=template_data, response_message=str(exc),
            )
            return self._reopen()

        self.result_message = json.dumps(result, ensure_ascii=False, indent=2)
        Log.create_log(
            template=self.template_id, phone=self.phone, source=source,
            state='success' if result.get('error') == 0 else 'error',
            sale_order=self.sale_order_id, tracking_id=self.tracking_id,
            template_data=template_data, error_code=result.get('error'),
            response_message=result.get('message'),
        )
        return self._reopen()

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
