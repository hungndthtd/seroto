# -*- coding: utf-8 -*-
"""
edu_care.py
CRM Care – Chăm sóc học viên sau khi nhập học.
Theo dõi: tình trạng học, tâm lý, tốc độ tiến bộ, hài lòng → Tái tư vấn / Upsell.
Luồng: Học viên → CRM Care → Phản hồi → Hành động follow-up → Upsell khoá mới.
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


# ─────────────────────────────────────────────────────────────────────────────
# Danh mục chăm sóc
# ─────────────────────────────────────────────────────────────────────────────
class EduCareCategory(models.Model):
    _name = 'edu.care.category'
    _description = 'Danh mục chăm sóc học viên'
    _order = 'sequence, name'

    name = fields.Char(string='Tên danh mục', required=True)
    sequence = fields.Integer(default=10)
    color = fields.Integer(string='Màu', default=0)
    description = fields.Text(string='Mô tả')


# ─────────────────────────────────────────────────────────────────────────────
# Hoạt động chăm sóc (Log tương tác)
# ─────────────────────────────────────────────────────────────────────────────
class EduCareActivity(models.Model):
    _name = 'edu.care.activity'
    _description = 'Hoạt động chăm sóc học viên'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_activity desc'

    name = fields.Char(
        string='Tiêu đề',
        required=True,
        compute='_compute_name',
        store=True,
        readonly=False,
    )
    student_id = fields.Many2one(
        'edu.student', string='Học viên', required=True, ondelete='cascade', tracking=True,
    )
    care_staff_id = fields.Many2one(
        'res.users', string='Nhân viên chăm sóc',
        default=lambda self: self.env.user, tracking=True,
    )
    category_id = fields.Many2one('edu.care.category', string='Danh mục')

    # ── Loại tương tác ────────────────────────────────────────────────────────
    activity_type = fields.Selection(
        selection=[
            ('call',        'Gọi điện'),
            ('sms',         'SMS / Zalo'),
            ('email',       'Email'),
            ('in_person',   'Gặp trực tiếp'),
            ('online_meet', 'Họp online'),
            ('parent_call', 'Liên hệ phụ huynh'),
            ('feedback',    'Thu thập phản hồi'),
            ('warning',     'Cảnh báo / Nhắc nhở'),
            ('upsell',      'Tư vấn khoá mới'),
            ('other',       'Khác'),
        ],
        string='Loại tương tác',
        required=True,
        default='call',
        tracking=True,
    )
    direction = fields.Selection(
        selection=[
            ('outbound', 'Chủ động liên hệ'),
            ('inbound',  'Học viên liên hệ'),
        ],
        string='Chiều tương tác',
        default='outbound',
    )

    date_activity = fields.Datetime(
        string='Thời gian',
        required=True,
        default=fields.Datetime.now,
        tracking=True,
    )
    duration_minutes = fields.Integer(string='Thời lượng (phút)')

    # ── Nội dung ────────────────────────────────────────────────────────────
    summary = fields.Text(string='Tóm tắt nội dung trao đổi', required=True)
    student_feedback = fields.Text(string='Phản hồi / Ý kiến của học viên')
    action_required = fields.Text(string='Hành động cần thực hiện')

    # ── Kết quả ────────────────────────────────────────────────────────────
    result = fields.Selection(
        selection=[
            ('positive',     'Tích cực – học viên hài lòng'),
            ('neutral',      'Bình thường'),
            ('negative',     'Tiêu cực – cần theo dõi'),
            ('no_answer',    'Không liên lạc được'),
            ('upsell_done',  'Đã tư vấn và đăng ký khoá mới'),
            ('at_risk',      'Nguy cơ nghỉ học'),
        ],
        string='Kết quả tương tác',
        tracking=True,
    )
    next_action_date = fields.Date(string='Ngày follow-up tiếp theo', tracking=True)
    next_action_note = fields.Text(string='Nội dung follow-up tiếp theo')

    # ── Liên kết ─────────────────────────────────────────────────────────────
    class_id = fields.Many2one(
        'edu.course.class', string='Lớp học liên quan',
        domain="[('enrollment_ids.student_id', '=', student_id)]",
    )
    crm_lead_id = fields.Many2one(
        'crm.lead', string='Lead / Cơ hội (Upsell)',
        ondelete='set null',
        help='Nếu tư vấn khoá mới thành công, tạo lead CRM mới tại đây',
    )
    attachment_ids = fields.Many2many('ir.attachment', string='Đính kèm')

    @api.depends('student_id', 'activity_type', 'date_activity')
    def _compute_name(self):
        type_labels = dict(self._fields['activity_type'].selection)
        for rec in self:
            date_str = fields.Datetime.to_string(rec.date_activity)[:10] if rec.date_activity else ''
            type_str = type_labels.get(rec.activity_type, '')
            student_str = rec.student_id.name if rec.student_id else ''
            rec.name = f"[{date_str}] {type_str} – {student_str}"


# ─────────────────────────────────────────────────────────────────────────────
# Phiếu phản hồi / Khảo sát mức độ hài lòng
# ─────────────────────────────────────────────────────────────────────────────
class EduCareFeedback(models.Model):
    _name = 'edu.care.feedback'
    _description = 'Phản hồi / Khảo sát học viên'
    _inherit = ['mail.thread']
    _order = 'date_feedback desc'

    name = fields.Char(string='Mã phản hồi', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'))
    student_id = fields.Many2one('edu.student', string='Học viên', required=True, ondelete='cascade')
    class_id = fields.Many2one('edu.course.class', string='Lớp học', ondelete='set null')
    teacher_id = fields.Many2one('edu.teacher', string='Giáo viên', ondelete='set null')

    date_feedback = fields.Date(string='Ngày phản hồi', default=fields.Date.today)
    feedback_type = fields.Selection(
        selection=[
            ('nps',         'NPS (Giới thiệu cho bạn bè)'),
            ('mid_course',  'Giữa khoá'),
            ('end_course',  'Cuối khoá'),
            ('ad_hoc',      'Phản hồi đột xuất'),
        ],
        string='Loại khảo sát',
        default='mid_course',
    )

    # ── Thang điểm NPS / hài lòng ────────────────────────────────────────────
    satisfaction_score = fields.Integer(
        string='Mức độ hài lòng (1-10)',
        help='1 = Rất không hài lòng, 10 = Rất hài lòng',
    )
    nps_score = fields.Integer(
        string='NPS (0-10)',
        help='Khả năng giới thiệu cho bạn bè (0-10)',
    )
    nps_category = fields.Selection(
        selection=[
            ('promoter',  'Người ủng hộ (9-10)'),
            ('passive',   'Thụ động (7-8)'),
            ('detractor', 'Người phàn nàn (0-6)'),
        ],
        string='Phân loại NPS',
        compute='_compute_nps_category',
        store=True,
    )

    # ── Đánh giá chi tiết ────────────────────────────────────────────────────
    teacher_rating = fields.Integer(string='Chất lượng giảng dạy (1-5)')
    content_rating = fields.Integer(string='Nội dung khoá học (1-5)')
    facility_rating = fields.Integer(string='Cơ sở vật chất (1-5)')
    schedule_rating = fields.Integer(string='Thời gian / Lịch học (1-5)')
    care_rating = fields.Integer(string='Chăm sóc học viên (1-5)')

    positive_comment = fields.Text(string='Điều học viên thích')
    improvement_comment = fields.Text(string='Điều cần cải thiện')
    referral_names = fields.Text(string='Tên bạn bè được giới thiệu')

    # ── Xử lý ─────────────────────────────────────────────────────────────────
    care_staff_id = fields.Many2one('res.users', string='Nhân viên xử lý')
    action_taken = fields.Text(string='Hành động đã thực hiện')
    is_resolved = fields.Boolean(string='Đã xử lý xong', default=False)

    @api.depends('nps_score')
    def _compute_nps_category(self):
        for rec in self:
            if rec.nps_score is not False:
                if rec.nps_score >= 9:
                    rec.nps_category = 'promoter'
                elif rec.nps_score >= 7:
                    rec.nps_category = 'passive'
                else:
                    rec.nps_category = 'detractor'
            else:
                rec.nps_category = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('edu.care.feedback') or _('New')
        return super().create(vals_list)

    @api.constrains('satisfaction_score')
    def _check_scores(self):
        for rec in self:
            if rec.satisfaction_score and not (1 <= rec.satisfaction_score <= 10):
                raise ValidationError(_('Điểm hài lòng phải từ 1 đến 10.'))
            if rec.nps_score is not False and not (0 <= rec.nps_score <= 10):
                raise ValidationError(_('Điểm NPS phải từ 0 đến 10.'))


# ─────────────────────────────────────────────────────────────────────────────
# Kế hoạch chăm sóc định kỳ
# ─────────────────────────────────────────────────────────────────────────────
class EduCareSchedule(models.Model):
    _name = 'edu.care.schedule'
    _description = 'Kế hoạch chăm sóc định kỳ'
    _inherit = ['mail.thread']
    _order = 'scheduled_date asc'

    name = fields.Char(string='Tiêu đề', required=True)
    student_id = fields.Many2one('edu.student', string='Học viên', required=True, ondelete='cascade')
    care_staff_id = fields.Many2one(
        'res.users', string='Nhân viên phụ trách',
        default=lambda self: self.env.user,
        tracking=True,
    )

    scheduled_date = fields.Date(string='Ngày chăm sóc dự kiến', required=True, tracking=True)
    care_type = fields.Selection(
        selection=[
            ('welcome',      'Chào mừng nhập học'),
            ('week_1',       'Tuần 1 – Kiểm tra thích nghi'),
            ('mid_course',   'Giữa khoá – Đánh giá tiến độ'),
            ('pre_exam',     'Trước kỳ thi – Động viên'),
            ('post_exam',    'Sau kỳ thi – Phân tích kết quả'),
            ('absent_alert', 'Cảnh báo vắng nhiều'),
            ('upsell',       'Tư vấn khoá nâng cao'),
            ('graduation',   'Tốt nghiệp / Kết thúc khoá'),
            ('periodic',     'Định kỳ'),
            ('custom',       'Tuỳ chỉnh'),
        ],
        string='Loại chăm sóc',
        required=True,
        default='periodic',
    )
    priority = fields.Selection(
        selection=[('0', 'Thấp'), ('1', 'Bình thường'), ('2', 'Cao'), ('3', 'Khẩn cấp')],
        string='Ưu tiên',
        default='1',
    )

    description = fields.Text(string='Nội dung cần trao đổi / Mục tiêu')
    state = fields.Selection(
        selection=[
            ('planned',    'Chờ thực hiện'),
            ('done',       'Đã thực hiện'),
            ('postponed',  'Dời lịch'),
            ('cancelled',  'Huỷ'),
        ],
        string='Trạng thái',
        default='planned',
        tracking=True,
    )
    activity_id = fields.Many2one(
        'edu.care.activity',
        string='Log tương tác kết quả',
        ondelete='set null',
        readonly=True,
    )
    date_done = fields.Date(string='Ngày thực hiện thực tế')
    note = fields.Text(string='Kết quả / Ghi chú')

    def action_mark_done(self):
        self.write({'state': 'done', 'date_done': fields.Date.today()})

    def action_postpone(self):
        self.write({'state': 'postponed'})
