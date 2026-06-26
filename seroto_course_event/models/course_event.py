from odoo import models, fields

class CourseEvent(models.Model):
  _inherit = 'event.event'

  course_title = fields.Char(
    string='Tên khóa học'
  )

  course_subtitle = fields.Char(
    string='Phụ đề'
  )

  course_type_ids = fields.Many2many(
    'course.event.type',
    string='Hình thức'
  )

  course_description = fields.Text(
    string='Mô tả'
  )

  teacher_partner_id = fields.Many2one(
    'res.partner',
    string='Giảng viên'
  )

  enrollment = fields.Char(
    string='Tuyển sinh'
  )

  registration_deadline = fields.Date(
    string='Thời hạn đăng ký'
  )

  register_url = fields.Char(
    string='Link đăng ký'
  )