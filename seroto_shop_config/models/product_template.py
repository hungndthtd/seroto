# -*- coding: utf-8 -*-

from odoo import api, models, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def write(self, vals):
        if vals.get('website_published'):
            for product in self:
                product._check_not_internal_only()
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for product, vals in zip(records, vals_list):
            if vals.get('website_published'):
                product._check_not_internal_only()
        return records

    def _check_not_internal_only(self):
        self.ensure_one()
        if self.is_donation_product:
            raise UserError(_(
                'Sản phẩm "%s" là sản phẩm Gieo hạt dùng nội bộ - không được đăng công khai lên Shop.'
            ) % self.name)
        course = self.env['academic.course'].sudo().search([('product_id', '=', self.id)], limit=1)
        if course:
            raise UserError(_(
                'Sản phẩm "%s" đang gắn với khóa học "%s" - không được đăng công khai lên Shop.'
            ) % (self.name, course.name))
