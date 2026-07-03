from odoo import models, fields


class SaleOrder(models.Model):
  _inherit = 'sale.order'

  student_id = fields.Many2one(
    comodel_name='seroto.student',
    string='Học viên',
    help='Học viên tương ứng với báo giá này - hiển thị trên form Báo giá '
         '(vd sau khi bấm "Báo giá mới" từ Lead).',
  )
