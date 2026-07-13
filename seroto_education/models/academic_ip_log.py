# -*- coding: utf-8 -*-

from odoo import models, fields

class AcademicIpLog(models.Model):
    _name = 'academic.ip.log'
    _description = 'Lịch sử IP đăng ký khóa học'

    ip_address = fields.Char(string='Địa chỉ IP', required=True, index=True)
    timestamp = fields.Datetime(string='Thời điểm gửi', default=fields.Datetime.now)
