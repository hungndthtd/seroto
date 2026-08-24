# -*- coding: utf-8 -*-

from odoo import models, fields, _


class AcademicBatchWizard(models.TransientModel):
    _name = 'academic.batch.wizard'
    _description = 'Mở đợt học mới'

    course_id = fields.Many2one('academic.course', string='Khóa học', required=True)
    intake_name = fields.Char(string='Mã đợt học', required=True, placeholder='K19')
    date_start = fields.Date(string='Ngày bắt đầu dự kiến')
    date_end = fields.Date(string='Ngày kết thúc dự kiến')
    teacher_ids = fields.Many2many('res.partner', string='Giảng viên', domain=[('is_teacher', '=', True)])
    set_as_default = fields.Boolean(string='Đặt làm lớp nhận đăng ký', default=True)
    # Gộp luôn bước "Mở đăng ký" vào wizard này - trước đây phải tạo đợt xong rồi tự vào
    # Lớp học bấm thêm 1 nút riêng mới website nhận đăng ký được, nay tick 1 lần là xong
    # cả 2 việc. Mặc định KHÔNG tick - vẫn đúng luồng cũ (tạo trước, rà lại thông tin,
    # chủ động công bố tuyển sinh sau khi sẵn sàng).
    open_registration = fields.Boolean(string='Mở cho phép đăng ký ngay')

    def action_confirm(self):
        self.ensure_one()
        intake = self.env['academic.intake'].create({
            'name': self.intake_name,
            'course_id': self.course_id.id,
            'date_start': self.date_start,
            'date_end': self.date_end,
        })
        new_class = self.env['academic.class'].create({
            'name': f"{self.course_id.name} - {self.intake_name}",
            'intake_id': intake.id,
            'teacher_ids': [(6, 0, self.teacher_ids.ids)],
            'state': 'draft',
        })
        if self.set_as_default:
            self.course_id.default_class_id = new_class.id

        if self.open_registration:
            new_class.state = 'open'
            # Tick "Mở cho phép đăng ký ngay" mà QUÊN tick "Đặt làm lớp nhận đăng ký" thì
            # website vẫn chưa nhận đăng ký được cho khóa này - nhắc rõ ngay tại đây,
            # đúng lúc dễ sửa nhất, thay vì để phát hiện muộn sau này.
            if self.course_id.default_class_id != new_class:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Lưu ý'),
                        'message': _(
                            'Lớp "%s" đã mở đăng ký nhưng CHƯA phải "Lớp nhận đăng ký" của '
                            'khóa học - website sẽ CHƯA cho đăng ký khóa này. Vào Khóa học, '
                            'đặt lớp này làm "Lớp nhận đăng ký" nếu muốn website nhận đăng '
                            'ký ngay.'
                        ) % new_class.name,
                        'type': 'warning',
                        'sticky': True,
                    },
                }

        return {'type': 'ir.actions.act_window_close'}
