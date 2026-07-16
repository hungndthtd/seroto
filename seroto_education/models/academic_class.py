import re

from odoo import models, fields, api

# Field "google_sheet_url" LƯU NGUYÊN link đầy đủ (không cắt xuống chỉ còn ID) - để hiển
# thị được dạng link bấm nhảy thẳng sang Sheet (widget="url" trong view) và nhân viên
# không rành kỹ thuật không phải biết "ID" là gì/lấy ở đâu, chỉ cần copy nguyên link từ
# thanh địa chỉ trình duyệt dán vào. Vẫn cho phép dán chỉ riêng ID trần (không có URL bao
# quanh) - tự bọc thành link đầy đủ khi lưu để luôn bấm được. ID thật (dùng để gọi Google
# Sheets API) được tách ra lúc cần dùng trong models/google_sheet_sync.py, không lưu
# riêng cột nào khác.
_SPREADSHEET_URL_RE = re.compile(r'/spreadsheets/d/([a-zA-Z0-9_-]+)')
_BARE_ID_RE = re.compile(r'^[a-zA-Z0-9_-]{20,}$')


def _normalize_sheet_url(value):
    if not value:
        return value
    value = value.strip()
    match = _SPREADSHEET_URL_RE.search(value)
    if match:
        return value
    if _BARE_ID_RE.match(value):
        return f'https://docs.google.com/spreadsheets/d/{value}/edit'
    return value


def _extract_id(url):
    match = _SPREADSHEET_URL_RE.search(url or '')
    return match.group(1) if match else ((url or '').strip() or False)


class AcademicClass(models.Model):
    _name = 'academic.class'
    _description = 'Lớp học'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Tên lớp học', required=True, tracking=True)
    course_id = fields.Many2one('academic.course', string='Khóa học', required=True, tracking=True)
    intake_id = fields.Many2one('academic.intake', string='Đợt học', required=True, tracking=True)
    teacher_ids = fields.Many2many('res.partner', string='Giảng viên', domain=[('is_teacher', '=', True)], tracking=True)
    active = fields.Boolean(string='Kích hoạt', default=True, tracking=True)
    
    session_ids = fields.One2many('academic.session', 'class_id', string='Các buổi học')
    enrollment_ids = fields.One2many('academic.enrollment', 'class_id', string='Học viên ghi danh')
    
    attendance_count = fields.Integer(string='Số lượt điểm danh', compute='_compute_attendance_count')
    date_start = fields.Date(string='Ngày bắt đầu', compute='_compute_dates', store=True)
    date_end = fields.Date(string='Ngày kết thúc', compute='_compute_dates', store=True)

    # Đồng bộ đăng ký từ Google Sheet (mỗi Lớp học/đợt tuyển sinh dùng 1 Google Form +
    # Spreadsheet riêng) - xem models/google_sheet_sync.py. Gắn ở CẤP LỚP HỌC (không
    # phải Khóa học) vì mỗi đợt mở lớp mới (K34, K35...) là 1 record riêng, tự nhiên
    # không đè lên Sheet của đợt cũ và không cần tự reset tiến độ đồng bộ.
    google_sheet_url = fields.Char(
        string='Link Google Sheet đăng ký',
        help='Dán NGUYÊN link Google Sheet (copy thẳng từ thanh địa chỉ trình duyệt). '
             'Bấm vào link để mở nhanh sang Sheet. Để trống = lớp này không nhận đăng '
             'ký qua Google Form, hoặc muốn TẠM DỪNG đồng bộ (xóa trắng ô này là dừng '
             'ngay, không ảnh hưởng gì tới dữ liệu/lịch sử đã đồng bộ trước đó).',
    )
    google_sheet_tab = fields.Char(
        string='Tên tab trong Sheet',
        help='Để trống = tự lấy tab ĐẦU TIÊN trong Spreadsheet (đúng cho hầu hết '
             'trường hợp, vì mỗi Spreadsheet ở đây thường chỉ có 1 tab response).',
    )
    google_sheet_last_row = fields.Integer(
        string='Đã đồng bộ tới dòng', default=1, copy=False,
        help='Tự cập nhật bởi cron đồng bộ, không cần sửa tay - trừ khi muốn đồng bộ '
             'lại từ đầu (đặt về 1) hoặc bỏ qua các dòng cũ.',
    )
    google_sheet_synced_id = fields.Char(
        string='Spreadsheet ID đã đồng bộ (nội bộ)', copy=False,
        help='ID Spreadsheet thật sự tương ứng với "Đã đồng bộ tới dòng" hiện tại - do '
             'cron tự ghi lại sau mỗi lần đồng bộ thành công (models/google_sheet_sync.py). '
             'Nếu "Link Google Sheet đăng ký" đổi sang 1 Spreadsheet KHÁC với ID này (kể '
             'cả sau khi đã xóa link rồi dán lại link khác), write() bên dưới sẽ tự reset '
             '"Đã đồng bộ tới dòng" về 1 để không bỏ sót dòng đầu của sheet mới. Không cần '
             'hiển thị/sửa tay field này.',
    )

    # Chỉ định TAY tên cột (vd "AO", "AP" - theo đúng ký hiệu cột Google Sheet) cho 3
    # thông tin cần lấy - dùng khi Sheet có nhiều cột dễ gây nhầm (vd vừa có "Số điện
    # thoại đại diện của nhóm" vừa có "Số điện thoại (SĐT có dùng Zalo)" của chính người
    # đăng ký) mà đoán tự động theo từ khóa dễ bắt nhầm cột. Để TRỐNG cả 3 = quay lại dùng
    # cách đoán tự động theo từ khóa tiêu đề (đủ dùng cho Sheet đơn giản, ít cột).
    google_sheet_col_name = fields.Char(
        string='Cột "Họ và tên"',
        help='Ký hiệu cột trong Google Sheet chứa Họ và tên (vd "AO"). Để trống = tự '
             'đoán theo từ khóa tiêu đề cột.',
    )
    google_sheet_col_phone = fields.Char(
        string='Cột "Số điện thoại"',
        help='Ký hiệu cột trong Google Sheet chứa đúng SĐT của người đăng ký (vd "AP") - '
             'cần điền tay nếu Sheet có nhiều cột SĐT khác nhau (vd SĐT người đại diện '
             'nhóm) để tránh lấy nhầm cột. Để trống = tự đoán theo từ khóa tiêu đề cột.',
    )
    google_sheet_col_email = fields.Char(
        string='Cột "Email"',
        help='Ký hiệu cột trong Google Sheet chứa Email (vd "C"). Để trống = tự đoán '
             'theo từ khóa tiêu đề cột.',
    )
    google_sheet_sync_confirmed = fields.Boolean(
        string='Đã xác nhận kích hoạt đồng bộ',
        help='Bắt buộc tick trước khi cron tự động đồng bộ Lớp học này - phòng trường '
             'hợp nhân viên mới dán Link/điền cột dở dang, chưa kiểm tra kỹ mà đã bị '
             'cron chạy nhầm, tạo sai dữ liệu Lead/Contact.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('google_sheet_url'):
                vals['google_sheet_url'] = _normalize_sheet_url(vals['google_sheet_url'])
        return super().create(vals_list)

    def write(self, vals):
        resetting_ids = []
        if 'google_sheet_url' in vals:
            new_url = _normalize_sheet_url(vals['google_sheet_url']) if vals['google_sheet_url'] else vals['google_sheet_url']
            vals = dict(vals, google_sheet_url=new_url)
            new_id = _extract_id(new_url) if new_url else False
            if new_id:
                for rec in self:
                    if new_id != rec.google_sheet_synced_id:
                        resetting_ids.append(rec.id)
        res = super().write(vals)
        if resetting_ids:
            # Đổi sang Spreadsheet KHÁC với sheet đã đồng bộ trước đó (dù có xóa link ở
            # giữa hay không) - reset lại tiến độ để không bỏ sót dòng đầu của sheet mới.
            # An toàn dù có đi vòng lại đúng sheet cũ trước đây: cơ chế chống trùng theo
            # "google_sheet_row_ref" trên crm.lead (xem google_sheet_sync.py) đảm bảo
            # không tạo Lead trùng nếu lỡ đọc lại các dòng đã xử lý.
            self.browse(resetting_ids).write({'google_sheet_last_row': 1})
        return res

    def init(self):
        super(AcademicClass, self).init()
        # Check date_start
        self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='academic_class' AND column_name='date_start'")
        if not self.env.cr.fetchone():
            self.env.cr.execute("ALTER TABLE academic_class ADD COLUMN date_start DATE")
            self.env.cr.commit()
        # Check date_end
        self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='academic_class' AND column_name='date_end'")
        if not self.env.cr.fetchone():
            self.env.cr.execute("ALTER TABLE academic_class ADD COLUMN date_end DATE")
            self.env.cr.commit()

    @api.depends('session_ids.date_start', 'session_ids.date_end')
    def _compute_dates(self):
        for rec in self:
            session_starts = rec.session_ids.filtered(lambda s: s.date_start).mapped('date_start')
            session_ends = rec.session_ids.filtered(lambda s: s.date_end).mapped('date_end')
            rec.date_start = min(session_starts).date() if session_starts else False
            rec.date_end = max(session_ends).date() if session_ends else False

    @api.depends('session_ids')
    def _compute_attendance_count(self):
        for rec in self:
            sessions = rec.session_ids
            if sessions:
                rec.attendance_count = self.env['academic.attendance'].search_count([('session_id', 'in', sessions.ids)])
            else:
                rec.attendance_count = 0

    def action_view_attendance(self):
        self.ensure_one()
        return {
            'name': 'Lịch sử điểm danh',
            'type': 'ir.actions.act_window',
            'res_model': 'academic.attendance',
            'view_mode': 'list,form',
            'domain': [('class_id', '=', self.id)],
            'context': {
                'search_default_group_by_session': 1,
            }
        }
