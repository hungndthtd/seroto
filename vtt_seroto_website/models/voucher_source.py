# -*- coding: utf-8 -*-

from odoo import fields, models


class SerotoVoucherSource(models.Model):
    """Nguồn voucher (diện "Voucher quà tặng" trên Phiếu đăng ký) - Quản lý tự thêm/sửa
    được, KHÔNG hardcode cứng trong code, vì danh sách nguồn thực tế có thể phát sinh
    thêm theo thời gian (VD thêm đối tác mới) - giống lý do "Diện đăng ký" tách ra bảng
    riêng thay vì hardcode.
    """
    _name = 'seroto.voucher.source'
    _description = 'Nguồn voucher quà tặng'
    _order = 'sequence, id'

    name = fields.Char(string='Tên nguồn voucher', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
