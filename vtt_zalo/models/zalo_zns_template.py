# -*- coding: utf-8 -*-

from datetime import date, datetime

from odoo import fields, models

# "Trường thông tin" của 1 tham số - CỐ TÌNH là danh sách CỐ ĐỊNH các field trên sale.order/
# res.partner/account.move (không phải field picker generic trên mọi model) - khớp đúng
# luồng thật: phiếu đăng ký khóa học (seroto.course.registration) khi thanh toán xong sẽ
# tự tạo ra 1 sale.order rồi hóa đơn tương ứng (xem vtt_seroto_website/models/
# course_registration.py, _create_sale_order/_auto_process_payment), nên đây luôn là nguồn
# dữ liệu để điền tham số ZNS, không cần tổng quát hoá sang model khác.
#
# 2 lựa chọn đặc biệt (KHÔNG map thẳng 1-1 sang field có sẵn của Odoo):
#   - 'order_cancel_reason': sale.order gốc KHÔNG có sẵn field "lý do hủy" chuẩn - đọc từ
#     field sale.order.cancel_reason do CHÍNH module này bổ sung (xem models/sale_order.py),
#     ghi vào lúc Sale xác nhận wizard "Lý do hủy đơn" (action_cancel_with_zalo_prompt).
#   - 'send_time': KHÔNG lấy từ field nào của đơn hàng/hóa đơn - là thời điểm hệ thống BẤM
#     GỬI (fields.Datetime.now() ngay lúc gọi API), không cố định theo bản ghi.
FIELD_SOURCE_SELECTION = [
    ('partner_name', '[Khách hàng] Tên khách hàng'),
    ('partner_phone', '[Khách hàng] Số điện thoại'),
    ('order_name', '[Đơn hàng] Mã đơn hàng'),
    ('order_date', '[Đơn hàng] Ngày đặt hàng'),
    ('order_amount_total', '[Đơn hàng] Tổng tiền'),
    ('order_state', '[Đơn hàng] Trạng thái'),
    ('invoice_name', '[Hóa đơn] Mã hóa đơn'),
    ('invoice_amount_total', '[Hóa đơn] Tổng tiền'),
    ('invoice_date', '[Hóa đơn] Ngày hóa đơn'),
    ('order_cancel_reason', '[Đơn hàng] Lý do hủy'),
    ('send_time', 'Giá trị theo thời gian khi bấm gửi'),
    ('manual', 'Tự nhập'),
]


class ZaloZnsTemplate(models.Model):
    """Khai lại (thủ công) các mẫu tin ZNS đã được Zalo duyệt trên Zalo Business - CHỈ lưu
    template_id + danh sách key tham số để tiện tra cứu/chọn khi gửi (xem
    zalo.send.zns.wizard), KHÔNG đồng bộ tự động 2 chiều với Zalo (Zalo không có API liệt
    kê mẫu tin đã duyệt kèm chi tiết tham số công khai để đồng bộ tự động).

    auto_send_event = 'payment_confirm' ĐÃ CÓ TRIGGER THẬT (xem models/account_move.py,
    _auto_send_zalo_zns_on_payment - hook payment_state chuyển paid/in_payment) - mỗi đơn
    hàng chỉ tự gửi 1 LẦN cho sự kiện này (xem sale.order.zalo_zns_payment_sent).

    auto_send_event = 'sale_cancel' CŨNG ĐÃ CÓ TRIGGER THẬT (xem models/sale_order.py,
    action_cancel_with_zalo_prompt - thay cho nút "Hủy" gốc trên form) - mở wizard hỏi "Lý
    do hủy đơn" trước khi hủy thật + tự gửi, KHÔNG áp dụng khi hủy hàng loạt từ list view
    (chỉ nút trên form mới đi qua wizard này).

    'sale_confirm' VẪN CHỈ LÀ METADATA - chưa có trigger (chưa override
    sale.order.action_confirm) - dành cho bước làm sau.

    Ở MỌI sự kiện: chỉ mẫu tin ĐANG KÍCH HOẠT (active=True) đầu tiên khớp mới được dùng.
    """
    _name = 'zalo.zns.template'
    _description = 'Mẫu tin ZNS'
    _order = 'name'

    name = fields.Char(string='Tên mẫu', required=True)
    active = fields.Boolean(string='Kích hoạt', default=True)
    template_id = fields.Char(
        string='ZNS Template Id', required=True,
        help='Đúng ID mẫu tin đã duyệt, xem trong Zalo Business > Mẫu tin ZNS.',
    )
    auto_send_event = fields.Selection([
        ('sale_confirm', 'Khi xác nhận đơn hàng'),
        ('payment_confirm', 'Khi xác nhận thanh toán'),
        ('sale_cancel', 'Khi đơn hàng bị hủy'),
    ], string='Sự kiện gửi tin tự động')
    preview_image = fields.Image(string='Ảnh xem trước')
    note = fields.Text(string='Ghi chú')
    param_ids = fields.One2many('zalo.zns.template.param', 'zns_template_id', string='Tham số')

    def _resolve_template_data(self, sale_order=None):
        """Tự build dict {key: value} để gửi ZNS - đọc field_source của từng tham số rồi
        lấy giá trị thật từ sale_order (nếu có), giống hệt cách zalo.send.zns.wizard đang
        gọi khi mở wizard kèm theo 1 đơn hàng (xem action_open_zalo_send_zns_wizard,
        models/sale_order.py). Không có sale_order (gửi thử không gắn đơn hàng) thì mọi
        field_source khác 'manual'/'send_time' trả về rỗng.
        """
        self.ensure_one()
        return {p.key: p._resolve_value(sale_order) for p in self.param_ids}


class ZaloZnsTemplateParam(models.Model):
    _name = 'zalo.zns.template.param'
    _description = 'Tham số của Mẫu tin ZNS'
    _order = 'sequence, id'

    zns_template_id = fields.Many2one(
        'zalo.zns.template', string='Mẫu tin', required=True, ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    key = fields.Char(
        string='Key', required=True,
        help='Đúng tên tham số trong mẫu đã duyệt, VD: order_code, customer_name...',
    )
    field_source = fields.Selection(
        FIELD_SOURCE_SELECTION, string='Trường thông tin', default='manual', required=True,
        help='Nguồn lấy giá trị tự động cho tham số này khi gửi tự động (xem lưu ý '
             'auto_send_event ở zalo.zns.template) - chọn "Tự nhập" để gõ tay 1 giá trị '
             'cố định (VD field "status" luôn là "Đã xác nhận").',
    )
    custom_value = fields.Char(
        string='Giá trị tùy chỉnh',
        help='Chỉ dùng khi Trường thông tin = "Tự nhập".',
    )
    value_type = fields.Selection([
        ('text', 'Chữ'),
        ('number', 'Số'),
        ('datetime', 'Ngày giờ'),
    ], string='Value type', default='text', required=True)
    description = fields.Char(string='Ghi chú', help='VD: 15:00:00 27/04/2026 - ghi chú định dạng mong muốn.')

    def _resolve_value(self, sale_order=None):
        """Trả về giá trị THẬT (đã format theo value_type) cho tham số này, đọc từ
        sale_order nếu field_source cần (xem _get_raw_value) - dùng chung cho cả gửi thủ
        công (kèm đơn hàng) lẫn gửi tự động sau này.
        """
        self.ensure_one()
        return self._format_value(self._get_raw_value(sale_order))

    def _get_raw_value(self, sale_order=None):
        self.ensure_one()
        if self.field_source == 'manual':
            return self.custom_value or ''
        if self.field_source == 'send_time':
            return fields.Datetime.now()
        if not sale_order:
            return ''

        partner = sale_order.partner_id
        # invoice_ids không đảm bảo thứ tự - lấy hóa đơn cuối cùng (mới nhất) cho đơn giản,
        # đủ dùng cho trường hợp phổ biến 1 đơn hàng chỉ có 1 hóa đơn.
        invoice = sale_order.invoice_ids[-1:] if sale_order.invoice_ids else sale_order.invoice_ids

        if self.field_source == 'partner_name':
            return partner.name
        if self.field_source == 'partner_phone':
            return partner.phone
        if self.field_source == 'order_name':
            return sale_order.name
        if self.field_source == 'order_date':
            return sale_order.date_order
        if self.field_source == 'order_amount_total':
            return sale_order.amount_total
        if self.field_source == 'order_state':
            selection = dict(self.env['sale.order'].fields_get(['state'])['state']['selection'])
            return selection.get(sale_order.state, sale_order.state)
        if self.field_source == 'invoice_name':
            return invoice.name if invoice else ''
        if self.field_source == 'invoice_amount_total':
            return invoice.amount_total if invoice else ''
        if self.field_source == 'invoice_date':
            return invoice.invoice_date if invoice else ''
        if self.field_source == 'order_cancel_reason':
            return sale_order.cancel_reason or ''
        return ''

    def _format_value(self, value):
        self.ensure_one()
        if self.value_type == 'datetime':
            if isinstance(value, datetime):
                return value.strftime('%H:%M:%S %d/%m/%Y')
            if isinstance(value, date):
                return value.strftime('%d/%m/%Y')
            return str(value) if value else ''
        if self.value_type == 'number':
            # sale.order.amount_total/account.move.amount_total là float (VD 10000.0) -
            # BỎ phần thập phân trước khi gửi (Zalo hiện "Giá tiền: 10000.0" xấu, tiền VND
            # không có lẻ) - làm tròn về số nguyên gần nhất rồi ép chuỗi.
            if value in (None, False, ''):
                return '0'
            try:
                return str(int(round(float(value))))
            except (TypeError, ValueError):
                return str(value)
        return str(value) if value not in (None, False) else ''
