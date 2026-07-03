# -*- coding: utf-8 -*-
"""
services/registration_service.py

Business logic của luồng WEBSITE → CRM Lead → edu.admission.
Controller (controllers/website_registration.py) chỉ đóng vai trò endpoint
mỏng: nhận request, gọi service, trả response — không chứa logic nghiệp vụ.
"""

from ..utils.choices import (
    ADMISSION_CHANNELS,
    EDUCATION_LEVELS,
    ENGLISH_LEVELS,
    PARENT_RELATIONSHIPS,
)


class RegistrationValidationError(Exception):
    """Lỗi validate dữ liệu form – mang theo danh sách lỗi để hiển thị lại cho người dùng."""

    def __init__(self, errors):
        self.errors = errors
        super().__init__('; '.join(errors))


class RegistrationService:
    """Toàn bộ nghiệp vụ đăng ký học qua website (form rút gọn + form đầy đủ)."""

    def __init__(self, env):
        self.env = env(su=True)

    # ─────────────────────────────────────────────────────────────────────
    # Khoá học / Lớp học
    # ─────────────────────────────────────────────────────────────────────
    def get_published_courses(self):
        return self.env['edu.course'].search([
            ('state', '=', 'published'),
            ('active', '=', True),
        ])

    def get_open_classes(self, course_id):
        return self.env['edu.course.class'].search([
            ('course_id', '=', course_id),
            ('state', 'in', ['scheduled', 'ongoing']),
            ('available_seats', '>', 0),
        ])

    def resolve_course_and_class(self, course_id, class_id):
        """Trả về (selected_course, classes, selected_class) cho trang form GET."""
        selected_course = None
        classes = self.env['edu.course.class']
        selected_class = None

        if course_id:
            try:
                course = self.env['edu.course'].browse(int(course_id))
            except (ValueError, TypeError):
                course = None
            if course and course.exists() and course.state == 'published':
                selected_course = course
                classes = self.get_open_classes(course.id)

        if class_id and selected_course:
            try:
                cls = self.env['edu.course.class'].browse(int(class_id))
            except (ValueError, TypeError):
                cls = None
            if cls and cls.exists():
                selected_class = cls

        return selected_course, classes, selected_class

    def get_classes_payload(self, course_id):
        """Payload JSON cho AJAX /dang-ky/get-classes."""
        if not course_id:
            return []
        classes = self.get_open_classes(int(course_id))
        return [{
            'id': c.id,
            'name': c.name,
            'date_start': c.date_start.strftime('%d/%m/%Y') if c.date_start else '',
            'schedule': c.schedule_note or '',
            'teacher': c.teacher_id.name if c.teacher_id else '',
            'available_seats': c.available_seats,
        } for c in classes]

    # ─────────────────────────────────────────────────────────────────────
    # Contact / Partner
    # ─────────────────────────────────────────────────────────────────────
    def find_or_create_partner(self, name, phone, email=None, street=None):
        partner = self.env['res.partner'].search([('phone', '=', phone)], limit=1)
        if not partner:
            partner = self.env['res.partner'].create({
                'name':   name,
                'phone':  phone,
                'email':  email or False,
                'street': street or False,
            })
        return partner

    def _get_website_source(self):
        return self.env['utm.source'].search([('name', 'ilike', 'website')], limit=1)

    # ─────────────────────────────────────────────────────────────────────
    # Form rút gọn – chỉ tạo CRM Lead
    # ─────────────────────────────────────────────────────────────────────
    def quick_register(self, post):
        name = post.get('name', '').strip()
        phone = post.get('phone', '').strip()
        if not name or not phone:
            raise RegistrationValidationError(['Vui lòng nhập Họ tên và Số điện thoại.'])

        partner = self.find_or_create_partner(name, phone, post.get('email', '').strip())

        course_id = int(post.get('course_id', 0) or 0)
        course_name = ''
        if course_id:
            course = self.env['edu.course'].browse(course_id)
            course_name = course.name if course.exists() else ''

        source = self._get_website_source()
        lead_name = f"[Đăng ký nhanh] {name}" + (f' – {course_name}' if course_name else '')
        self.env['crm.lead'].create({
            'name':         lead_name,
            'partner_id':   partner.id,
            'contact_name': name,
            'phone':        phone,
            'email_from':   post.get('email', '').strip() or False,
            'description':  f'Khoá học quan tâm: {course_name}' if course_name else '',
            'source_id':    source.id if source else False,
            'course_id':    course_id or False,
            'type':         'lead',
        })
        return name

    # ─────────────────────────────────────────────────────────────────────
    # Form đầy đủ – tạo CRM Lead + edu.admission
    # ─────────────────────────────────────────────────────────────────────
    def register_full(self, post):
        errors = self._validate_full_registration(post)
        if errors:
            raise RegistrationValidationError(errors)

        phone = post.get('phone', '').strip()
        partner = self.find_or_create_partner(
            post.get('student_name', '').strip(), phone,
            post.get('email', '').strip(), post.get('current_address', '').strip(),
        )

        course_id = int(post.get('course_id', 0) or 0)
        class_id = int(post.get('class_id', 0) or 0) or False
        course = self.env['edu.course'].browse(course_id) if course_id else None
        tuition_fee = course.tuition_fee if course and course.exists() else 0.0
        course_name = course.name if course and course.exists() else ''

        source = self._get_website_source()
        lead_name = f"[Đăng ký web] {post.get('student_name','').strip()} – {course_name}"
        lead = self.env['crm.lead'].create({
            'name':         lead_name,
            'partner_id':   partner.id,
            'contact_name': post.get('student_name', '').strip(),
            'phone':        phone,
            'email_from':   post.get('email', '').strip() or False,
            'description':  self._build_lead_description(post),
            'source_id':    source.id if source else False,
            'course_id':    course_id or False,
            'type':         'lead',
            'tag_ids':      [],
        })

        admission = self.env['edu.admission'].create({
            'student_name':        post.get('student_name', '').strip(),
            'phone':               phone,
            'email':               post.get('email', '').strip() or False,
            'date_of_birth':       post.get('date_of_birth') or False,
            'gender':              post.get('gender') or False,
            'id_number':           post.get('id_number', '').strip() or False,
            'address':             post.get('address', '').strip() or False,
            'current_address':     post.get('current_address', '').strip() or False,
            'education_level':     post.get('education_level') or False,
            'current_job':         post.get('current_job', '').strip() or False,
            'workplace':           post.get('workplace', '').strip() or False,
            'english_level':       post.get('english_level') or False,
            'target_cert':         post.get('target_cert', '').strip() or False,
            'target_score':        float(post.get('target_score', 0) or 0),
            'learning_goal':       post.get('learning_goal', '').strip() or False,
            'course_id':           course_id or False,
            'course_class_id':     class_id,
            'admission_channel':   post.get('admission_channel') or False,
            'referred_by':         post.get('referred_by', '').strip() or False,
            'parent_name':         post.get('parent_name', '').strip() or False,
            'parent_phone':        post.get('parent_phone', '').strip() or False,
            'parent_relationship': post.get('parent_relationship') or False,
            'tuition_fee':         tuition_fee,
            'partner_id':          partner.id,
            'crm_lead_id':         lead.id,
            'note':                post.get('note', '').strip() or False,
            'source_id':           source.id if source else False,
        })

        lead.description = (lead.description or '') + f'\n\n[Mã hồ sơ: {admission.name}]'
        return admission, partner

    # ─────────────────────────────────────────────────────────────────────
    # Tra cứu hồ sơ
    # ─────────────────────────────────────────────────────────────────────
    def lookup(self, keyword):
        if not keyword:
            return self.env['edu.admission']
        return self.env['edu.admission'].search([
            '|', ('phone', '=', keyword), ('email', '=', keyword),
        ], limit=10)

    # ─────────────────────────────────────────────────────────────────────
    # Context dùng chung cho trang form (GET lần đầu hoặc khi báo lỗi)
    # ─────────────────────────────────────────────────────────────────────
    def build_form_context(self, extra=None):
        ctx = {
            'courses': self.get_published_courses(),
            'classes': [],
            'selected_course': None,
            'selected_class': None,
            'admission_channels': ADMISSION_CHANNELS,
            'english_levels': ENGLISH_LEVELS,
            'education_levels': EDUCATION_LEVELS,
            'parent_relationships': PARENT_RELATIONSHIPS,
            'page_title': 'Form đăng ký học',
            'errors': [],
            'form_data': {},
        }
        if extra:
            ctx.update(extra)
        return ctx

    # ─────────────────────────────────────────────────────────────────────
    # Helpers nội bộ
    # ─────────────────────────────────────────────────────────────────────
    @staticmethod
    def _validate_full_registration(post):
        required_fields = {
            'student_name': 'Họ và tên học viên',
            'phone':        'Số điện thoại',
            'course_id':    'Khoá học quan tâm',
        }
        errors = []
        for field, label in required_fields.items():
            if not post.get(field, '').strip():
                errors.append(f'Vui lòng nhập <b>{label}</b>.')

        phone = post.get('phone', '').strip()
        if phone and len(phone.replace(' ', '').replace('-', '')) < 9:
            errors.append('Số điện thoại không hợp lệ.')
        return errors

    @staticmethod
    def _build_lead_description(post):
        lines = [
            f"Họ tên: {post.get('student_name','')}",
            f"SĐT: {post.get('phone','')}",
            f"Email: {post.get('email','')}",
            f"Ngày sinh: {post.get('date_of_birth','')}",
            f"Trình độ: {post.get('english_level','')}",
            f"Mục tiêu: {post.get('target_cert','')} – {post.get('target_score','')}",
            f"Kênh biết đến: {post.get('admission_channel','')}",
            f"Được giới thiệu bởi: {post.get('referred_by','')}",
            f"Ghi chú: {post.get('note','')}",
        ]
        return '\n'.join(l for l in lines if l.split(': ', 1)[-1].strip())
