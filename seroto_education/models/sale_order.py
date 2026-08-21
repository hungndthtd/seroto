# -*- coding: utf-8 -*-

from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            order.order_line._sync_enrollment()
            # Automatically mark the linked CRM Lead/Opportunity as Won
            if hasattr(order, 'opportunity_id') and order.opportunity_id:
                order.opportunity_id.action_set_won()
        return res


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    student_id = fields.Many2one(
        'res.partner', 
        string='Học viên', 
        domain="[('is_company', '=', False), '|', ('id', '=', parent.partner_id), ('parent_id', '=', parent.partner_id)]"
    )
    class_id = fields.Many2one('academic.class', string='Lớp học')

    # Link product template course to class domain
    @api.onchange('product_id')
    def _onchange_product_id_course(self):
        if self.product_id:
            course = self.env['academic.course'].search([('product_id', '=', self.product_id.product_tmpl_id.id)], limit=1)
            if course:
                if not self.class_id:
                    lead = self.order_id.opportunity_id
                    if lead and lead.class_id and lead.class_id.course_id == course:
                        self.class_id = lead.class_id
                    elif course.default_class_id:
                        self.class_id = course.default_class_id
                return {'domain': {'class_id': [('course_id', '=', course.id)]}}
        return {'domain': {'class_id': []}}

    @api.model_create_multi
    def create(self, vals_list):
        lines = super(SaleOrderLine, self).create(vals_list)
        lines._sync_enrollment()
        return lines

    def _prepare_invoice_line(self, **optional_values):
        # Đồng bộ "Lớp học" từ dòng Đơn hàng sang dòng Hóa đơn khi tạo hóa đơn - Odoo
        # mặc định KHÔNG tự copy field tùy biến này. Ghi danh/Báo cáo tổng hợp vốn đã
        # đọc đúng qua dòng Đơn hàng gốc dù thiếu bước này (xem academic_report_metric.py),
        # đây chỉ để cột "Lớp học" trên hóa đơn hiển thị khớp, tránh gây hiểu nhầm là
        # thiếu dữ liệu.
        vals = super()._prepare_invoice_line(**optional_values)
        if self.class_id:
            vals['class_id'] = self.class_id.id
        return vals

    def write(self, vals):
        res = super(SaleOrderLine, self).write(vals)
        if 'class_id' in vals or 'student_id' in vals:
            self._sync_enrollment()
        return res

    def _sync_enrollment(self):
        for line in self:
            if line.order_id.state == 'sale' and line.product_id and line.class_id:
                course = self.env['academic.course'].search([('product_id', '=', line.product_id.product_tmpl_id.id)], limit=1)
                if course:
                    student = line.student_id or line.order_id.partner_id
                    existing = self.env['academic.enrollment'].search([
                        ('student_id', '=', student.id),
                        ('class_id', '=', line.class_id.id),
                    ])
                    if not existing:
                        # Determine state based on invoice payment
                        invoice_paid = any(inv.payment_state in ('paid', 'in_payment') for inv in line.order_id.invoice_ids)
                        state = 'enrolled' if invoice_paid else 'draft'
                        self.env['academic.enrollment'].create({
                            'student_id': student.id,
                            'class_id': line.class_id.id,
                            'sale_order_id': line.order_id.id,
                            'state': state,
                        })
