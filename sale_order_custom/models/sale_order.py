from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    x_custom_note = fields.Text(string='Note')