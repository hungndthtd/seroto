# -*- coding: utf-8 -*-

from odoo import models, fields

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    course_id = fields.Many2one('academic.course', string='Khóa học quan tâm')
    class_id = fields.Many2one(
        'academic.class', string='Lớp học quan tâm',
        help='Lớp nhận đăng ký của khóa học tại thời điểm khách đăng ký trên website.',
    )
