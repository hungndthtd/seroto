from odoo import models, fields

class CourseEventType(models.Model):
  _name = 'course.event.type'
  _description = 'Course Type'

  name = fields.Char(
    required=True
  )

  color = fields.Integer()