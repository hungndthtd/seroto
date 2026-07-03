# -*- coding: utf-8 -*-
"""
crm_lead.py
Mở rộng crm.lead để gắn Lead với khoá học quan tâm và cho phép
chuyển Lead đủ điều kiện thành Hồ sơ tuyển sinh (edu.admission)
mà không phải nhập lại thông tin.
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    course_id = fields.Many2one(
        comodel_name='edu.course',
        string='Khoá học quan tâm',
    )
    edu_admission_id = fields.Many2one(
        comodel_name='edu.admission',
        string='Hồ sơ tuyển sinh',
        readonly=True,
        copy=False,
    )

    def action_create_edu_admission(self):
        """Chuyển Lead đủ điều kiện → tạo Hồ sơ tuyển sinh, kế thừa dữ liệu đã có."""
        self.ensure_one()
        if self.edu_admission_id:
            return self.action_view_edu_admission()

        partner = self.partner_id
        if not partner:
            name = self.contact_name or self.partner_name or self.name
            if not name or not self.phone:
                raise UserError(_(
                    'Vui lòng nhập Tên liên hệ và Số điện thoại trước khi chuyển đổi.'
                ))
            partner = self.env['res.partner'].sudo().search(
                [('phone', '=', self.phone)], limit=1
            )
            if not partner:
                partner = self.env['res.partner'].sudo().create({
                    'name':  name,
                    'phone': self.phone,
                    'email': self.email_from or False,
                })
            self.partner_id = partner.id

        admission = self.env['edu.admission'].create({
            'student_name': self.contact_name or self.partner_name or partner.name,
            'phone':        self.phone or partner.phone,
            'email':        self.email_from or partner.email,
            'course_id':    self.course_id.id,
            'partner_id':   partner.id,
            'crm_lead_id':  self.id,
            'source_id':    self.source_id.id,
            'medium_id':    self.medium_id.id,
            'campaign_id':  self.campaign_id.id,
        })
        self.edu_admission_id = admission.id
        self.message_post(body=_(
            'Đã chuyển thành Hồ sơ tuyển sinh <a href="#" data-oe-model="edu.admission" '
            'data-oe-id="%(id)s">%(name)s</a>.',
            id=admission.id, name=admission.name,
        ))
        return self.action_view_edu_admission()

    def action_view_edu_admission(self):
        self.ensure_one()
        return {
            'type':     'ir.actions.act_window',
            'name':     'Hồ sơ tuyển sinh',
            'res_model': 'edu.admission',
            'res_id':   self.edu_admission_id.id,
            'view_mode': 'form',
        }
