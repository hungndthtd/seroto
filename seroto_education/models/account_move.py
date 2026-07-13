# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('amount_residual', 'move_type', 'state', 'company_id', 'reconciled_payment_ids.state')
    def _compute_payment_state(self):
        super(AccountMove, self)._compute_payment_state()
        self._sync_enrollments_on_payment()

    def write(self, vals):
        res = super(AccountMove, self).write(vals)
        if 'payment_state' in vals:
            self._sync_enrollments_on_payment()
        return res

    def _sync_enrollments_on_payment(self):
        for move in self:
            if move.payment_state in ('paid', 'in_payment'):
                sale_orders = move.line_ids.sale_line_ids.order_id
                for order in sale_orders:
                    # 1. First sync/create enrollments for lines that have class_id set but no enrollment yet
                    order.order_line._sync_enrollment()
                    # 2. Then active all draft enrollments for this order
                    enrollments = self.env['academic.enrollment'].search([
                        ('sale_order_id', '=', order.id),
                        ('state', '=', 'draft')
                    ])
                    if enrollments:
                        enrollments.write({'state': 'enrolled'})
