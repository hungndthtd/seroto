# -*- coding: utf-8 -*-

from odoo import models, fields

class AcademicIntake(models.Model):
    _name = 'academic.intake'
    _description = 'Đợt học'

    name = fields.Char(string='Tên đợt học', required=True)
    date_start = fields.Date(string='Ngày bắt đầu')
    date_end = fields.Date(string='Ngày kết thúc')
    active = fields.Boolean(string='Kích hoạt', default=True)
