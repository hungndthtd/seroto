# -*- coding: utf-8 -*-

from odoo import models, fields

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    course_id = fields.Many2one('academic.course', string='Khóa học quan tâm')
