# -*- coding: utf-8 -*-

from odoo import models, fields

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    course_id = fields.Many2one('academic.course', string='Khóa học quan tâm')
    class_id = fields.Many2one(
        'academic.class', string='Lớp học/Đợt đăng ký',
        help='Lớp học (đợt tuyển sinh) cụ thể mà lead này đăng ký - điền tự động khi '
             'đồng bộ từ Google Sheet gắn ở academic.class (vd "Thực hành EQ K34").',
    )
    google_sheet_row_ref = fields.Char(
        string='Dòng Google Sheet nguồn', index=True, copy=False,
        help='Định danh duy nhất "<id Lớp học>:<số dòng Sheet>" đã tạo ra lead này (đồng '
             'bộ định kỳ qua google.sheet.sync) - dùng để tránh tạo trùng lead nếu cron '
             'chạy lại đúng dòng đó (vd do lỗi giữa chừng trước khi kịp lưu tiến độ).',
    )

    # Thông tin bổ sung nhân viên tự điền TAY trong Odoo trong quá trình làm việc/trao đổi
    # với học viên (KHÔNG đọc từ Google Sheet) - đặt trên crm.lead (ứng với TỪNG LẦN đăng
    # ký) chứ không đặt trên Contact học viên, vì 1 học viên có thể đăng ký nhiều khóa và
    # người ký/người đại diện nhóm có thể khác nhau mỗi lần đăng ký.
    signer_name = fields.Char(string='Họ tên người ký giấy xác nhận')
    signer_phone = fields.Char(string='SĐT người ký giấy xác nhận')
    signer_position = fields.Char(string='Chức vụ người ký')
    confirmation_doc_url = fields.Char(
        string='Link Giấy xác nhận (có chữ ký, đóng dấu)',
        help='Dán link tài liệu đã có sẵn (vd Google Drive) - dùng cách này HOẶC tải file '
             'lên trực tiếp ở field bên dưới, không cần điền cả 2.',
    )
    confirmation_doc_file = fields.Binary(string='Tải lên Giấy xác nhận', attachment=True)
    confirmation_doc_filename = fields.Char(string='Tên file Giấy xác nhận')
    group_rep_name = fields.Char(
        string='Họ tên người đại diện nhóm',
        help='Để trống nếu đây là đăng ký lẻ (không phải đăng ký theo nhóm).',
    )
    group_rep_phone = fields.Char(string='SĐT người đại diện nhóm')

    # Mục "Cam kết" - checkbox xác nhận cam kết của học viên, mặc định tick sẵn (mang tính
    # xác nhận/thừa nhận, không phải câu hỏi trung lập) - riêng biệt với nhóm field bên
    # dưới (thông tin phân loại đăng ký/ưu đãi, không phải cam kết).
    commit_read_course_info = fields.Boolean(
        string='Đã đọc kỹ thông tin khóa học', default=True,
    )
    commit_zoom_ontime = fields.Boolean(
        string='Cam kết học Zoom đúng giờ và học đủ', default=True,
    )
    commit_practice_submit = fields.Boolean(
        string='Cam kết thực hành đầy đủ, gửi kết quả đúng giờ', default=True,
    )
    commit_support_teammates = fields.Boolean(
        string='Cam kết sẽ đồng hành cùng đồng đội, cùng chăm sóc nhau', default=True,
    )
    commit_balanced_planting = fields.Boolean(
        string='Cam kết gieo hạt quân bình', default=True,
    )
    commit_allow_media_usage = fields.Text(
        string='Đồng ý cho BTC sử dụng hình ảnh',
    )

    # Mục "Ưu đãi & Phân loại đăng ký" - thông tin phân loại/ưu đãi của lần đăng ký này,
    # nhân viên điền tay bình thường (không mặc định tick).
    previously_studied = fields.Char(string='Đã từng học các khóa của Seroto trước đây')
    tuition_scholarship_category = fields.Char(
        string='Đăng ký học theo diện',
        help='Vd: Đóng học phí, Xét duyệt học bổng,...',
    )
    scholarship_reason = fields.Text(string='Lý do xứng đáng nhận học bổng khóa học')
    early_registration = fields.Char(
        string='Đăng ký theo diện',
    )
    registration_channel = fields.Char(string='Quyết định đăng ký khóa học qua kênh')
    voucher_recipient = fields.Char(string='Đối tượng nhận voucher')
    voucher_code = fields.Char(string='Mã voucher quà tặng')

    # Mục "Thanh toán" - riêng biệt với Giấy xác nhận/Ưu đãi (bằng chứng đã chuyển khoản
    # học phí, không phải giấy tờ cam kết hay phân loại ưu đãi).
    payment_proof_image = fields.Image(string='Ảnh chuyển khoản')
