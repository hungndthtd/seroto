# -*- coding: utf-8 -*-
from odoo import models, fields, api
import json

class WebsiteCustomBackground(models.Model):
    _name = 'website.custom.background'
    _description = 'Custom Website Background Design'
    _order = 'id desc'

    name = fields.Char(string='Name', required=True)
    website_id = fields.Many2one('website', string='Website', default=lambda self: self.env['website'].get_current_website(), required=True, ondelete='cascade')
    config_json = fields.Text(string='Configuration JSON', required=True, default='[]')
    compiled_css = fields.Text(string='Compiled CSS Style', required=True, default='')
    compiled_svg = fields.Text(string='Compiled SVG Content')
