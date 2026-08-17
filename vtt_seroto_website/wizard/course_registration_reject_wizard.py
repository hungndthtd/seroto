# -*- coding: utf-8 -*-

from odoo import models, fields


class CourseRegistrationRejectWizard(models.TransientModel):
    _name = 'seroto.course.registration.reject.wizard'
    _description = 'Từ chối phiếu đăng ký khóa học'

    registration_id = fields.Many2one('seroto.course.registration', string='Phiếu đăng ký', required=True)
    reason = fields.Text(string='Lý do từ chối', required=True)

    def action_confirm(self):
        self.ensure_one()
        self.registration_id.write({
            'state': 'rejected',
            'reject_reason': self.reason,
        })
        return {'type': 'ir.actions.act_window_close'}
