# -*- coding: utf-8 -*-
from odoo import models, fields, api

class WebsiteCustomSvg(models.Model):
    _name = 'website.custom.svg'
    _description = 'Website Custom SVG Library'
    _order = 'name, id'

    name = fields.Char(string='Tên SVG', required=True)
    svg_code = fields.Text(string='Mã SVG', required=True)
    color = fields.Char(string='Màu mặc định', default='#333333')
    website_id = fields.Many2one('website', string='Website', ondelete='cascade')
