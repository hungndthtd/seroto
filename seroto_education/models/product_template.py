# -*- coding: utf-8 -*-

from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Đánh dấu sản phẩm dùng để ghi nhận Gieo hạt (đóng góp tự nguyện) trên Đơn
    # hàng/Hóa đơn - academic_report_metric.py dựa vào field này để gom các dòng
    # hóa đơn liên quan vào loại số liệu "Gieo hạt" (không dùng model riêng nữa,
    # tái sử dụng luôn quy trình Đơn hàng -> Hóa đơn -> Đăng ký thanh toán đã quen
    # thuộc, tránh phải hiểu thêm về Phiếu thu/Sổ nhật ký kế toán).
    is_donation_product = fields.Boolean(string='Là sản phẩm Gieo hạt')
