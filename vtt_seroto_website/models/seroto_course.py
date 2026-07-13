import re
import unicodedata

from odoo import models, _
from odoo.exceptions import UserError


class SerotoCourse(models.Model):
  _inherit = 'seroto.course'

  # Tính năng "Tạo trang landing" tách riêng sang vtt_seroto_website (thay vì để
  # trong seroto_form) vì cần env.ref tới view seroto_form đã KHÔNG THỂ phụ thuộc
  # ngược vtt_seroto_website (seroto_form không được phép phụ thuộc module con đang
  # phụ thuộc chính nó). Nút bấm tương ứng cũng chuyển sang view kế thừa trong
  # views/seroto_course_views.xml của module này.

  def _slugify_name(self):
    """Chuyển 'Tên khóa học' thành dạng URL an toàn (bỏ dấu, khoảng trắng -> '-')."""
    self.ensure_one()
    text = (self.name or '').replace('đ', 'd').replace('Đ', 'D')
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    text = re.sub(r'[-\s]+', '-', text)
    return text or 'khoa-hoc'

  def action_create_landing_page(self):
    """Tạo 1 trang landing (website.page) MỚI cho khóa học này từ mẫu
    vtt_seroto_website.page_maukhoahoc - xem ghi chú chi tiết trong
    views/pages/page_maukhoahoc.xml. Chỉ điền được Tên khóa học + Hình thức học lúc
    này (chưa có lớp học nào để lấy lịch/hạn đăng ký) - phần còn lại staff tự điền qua
    Website Editor sau khi trang được tạo.
    """
    self.ensure_one()

    if self.landing_page_url:
      raise UserError(_(
        'Khóa học "%(name)s" đã có trang landing (%(url)s). Xóa field "Trang landing" '
        'trước nếu muốn tạo trang mới (trang cũ sẽ KHÔNG bị xóa tự động).',
        name=self.name, url=self.landing_page_url,
      ))

    template_view = self.env.ref('vtt_seroto_website.page_maukhoahoc_view')
    course_type_labels = dict(self._fields['course_type'].selection)
    new_key = 'vtt_seroto_website.page_course_%s' % self.id

    # Thay chuỗi CHÍNH XÁC khớp placeholder trong page_maukhoahoc.xml - xem lưu ý ở
    # đầu file đó nếu cần đổi placeholder text.
    arch = template_view.arch
    arch = arch.replace('t-name="vtt_seroto_website.page_maukhoahoc"', 't-name="%s"' % new_key)
    arch = arch.replace('[TÊN KHÓA HỌC]', self.name or '')
    arch = arch.replace('[HÌNH THỨC HỌC]', course_type_labels.get(self.course_type, ''))
    arch = arch.replace('data-price="0"', 'data-price="%s"' % (self.tuition_fee or 0))
    # Chưa có lớp học lúc tạo trang nên chưa biết giờ/ngày/hạn đăng ký thật - để "Sắp
    # công bố" thay vì giữ nguyên placeholder dạng ngoặc vuông trông như lỗi chưa điền.
    arch = arch.replace('[hh:mm - hh:mm]', 'Sắp công bố')
    arch = arch.replace('[dd/mm - dd/mm/yyyy]', 'Sắp công bố')
    arch = arch.replace('[dd/mm/yyyy]', 'Sắp công bố')
    # "Phụ đề" (subtitle) đóng vai trò mô tả ngắn 1-2 câu - có thì thay vào, không có
    # thì giữ nguyên câu mẫu để staff biết chỗ đó cần tự viết mô tả qua Website Editor.
    if self.subtitle:
      arch = arch.replace('Mô tả ngắn 1-2 câu về khóa học', self.subtitle)

    new_view = self.env['ir.ui.view'].sudo().create({
      'name': 'Page - %s' % self.name,
      'type': 'qweb',
      'key': new_key,
      'arch': arch,
    })

    url = '/%s' % self._slugify_name()

    # Không kèm id vào URL vì tên khóa học (vd "EQ 5 phút K19") đã coi là duy nhất -
    # chặn sớm nếu 2 khóa học lỡ trùng tên (sau khi bỏ dấu) để tránh 2 trang cùng URL.
    if self.env['website.page'].sudo().search_count([('url', '=', url)]):
      raise UserError(_(
        'Đã có 1 trang khác dùng URL "%(url)s" (trùng tên khóa học sau khi bỏ dấu). '
        'Đổi Tên khóa học cho khác biệt hơn rồi thử lại.',
        url=url,
      ))

    page = self.env['website.page'].sudo().create({
      'name': self.name,
      'url': url,
      'view_id': new_view.id,
      # Chưa publish ngay - trang còn thiếu lịch học/giá chi tiết, để staff hoàn thiện
      # qua Website Editor rồi tự bấm "Xuất bản" khi sẵn sàng.
      'is_published': False,
      # Trang khóa học có Footer riêng viết tay trong page_maukhoahoc.xml, không dùng
      # chung Header/Footer chuẩn của site (trang landing tập trung vào CTA, không
      # muốn menu điều hướng làm phân tán khách).
      'header_visible': False,
      'footer_visible': False,
    })

    # BƯỚC 2: chỉ biết url thật SAU KHI website.page đã tạo xong - ghi đè lại arch lần
    # nữa để điền nốt link "Website" trong Footer (xem [URL_TRANG] trong
    # page_maukhoahoc.xml).
    new_view.arch = new_view.arch.replace('[URL_TRANG]', page.url)

    self.landing_page_url = page.url

    return {
      'type': 'ir.actions.act_url',
      'url': page.url,
      'target': 'new',
    }
