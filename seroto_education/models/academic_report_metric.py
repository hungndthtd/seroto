# -*- coding: utf-8 -*-

from odoo import fields, models, tools


class AcademicReportMetric(models.Model):
    """Báo cáo tổng hợp theo khóa học - gộp 6 nguồn dữ liệu (Ghi danh, Hoàn thành,
    Người phụng sự, Gieo hạt, Thu, Chi) về chung 1 model dạng "long" (mỗi dòng = 1
    lượt phát sinh của 1 loại số liệu) để xem Pivot theo Khóa học x Tháng/Năm x Loại
    số liệu trên cùng 1 màn hình, thay vì phải mở riêng từng menu rồi tự cộng tay.

    "Chi" tổng hợp qua field "Lớp học" (class_id) gắn thẳng trên dòng hóa đơn nhà cung
    cấp (xem account_move.py, AccountMoveLine.class_id) - không dùng Kế toán phân tích
    chuẩn của Odoo vì giao diện đó chỉ có ở app Kế toán Enterprise. Cộng dồn tự nhiên lên
    Khóa học khi nhóm theo course_id ở Pivot. Chi phí KHÔNG gắn Lớp học nào (chi phí
    chung/ngoài phạm vi) sẽ không xuất hiện trong báo cáo này, theo đúng phạm vi đã
    thống nhất.

    "Gieo hạt" tổng hợp qua dòng hóa đơn bán hàng dùng đúng Sản phẩm được đánh dấu
    "Là sản phẩm Gieo hạt" (product_template.is_donation_product, xem
    product_template.py) - KHÔNG dùng model riêng/Phiếu thu (account.payment) nữa vì
    đòi hỏi hiểu thêm về Sổ nhật ký kế toán, vốn không phù hợp khi phần mềm chỉ cài
    Hóa đơn (Invoicing) Community. Tái sử dụng đúng quy trình Đơn hàng -> Hóa đơn ->
    Đăng ký thanh toán đã quen thuộc (giống hệt "Thu").
    """
    _name = 'academic.report.metric'
    _description = 'Báo cáo tổng hợp theo khóa học'
    _auto = False
    _order = 'date desc'

    course_id = fields.Many2one('academic.course', string='Khóa học', readonly=True)
    class_id = fields.Many2one(
        'academic.class', string='Lớp học', readonly=True,
        help='Với loại "Thu"/"Gieo hạt": lấy từ cột "Lớp học" chọn trực tiếp trên dòng hóa đơn, nếu trống thì lấy qua dòng Đơn hàng gốc (nếu hóa đơn được tạo từ Đơn hàng) - để trống cả 2 nơi thì không xuất hiện ở đây.',
    )
    date = fields.Date(string='Ngày', readonly=True)
    metric_type = fields.Selection([
        ('participant', 'Học viên tham gia'),
        ('completed', 'Hoàn thành'),
        ('volunteer', 'Người phụng sự'),
        ('donation', 'Gieo hạt'),
        ('revenue', 'Thu (học phí)'),
        ('expense', 'Chi'),
    ], string='Loại số liệu', readonly=True)
    count_value = fields.Integer(string='Số lượng', readonly=True)
    amount_value = fields.Monetary(string='Số tiền', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Đơn vị tiền tệ', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW academic_report_metric AS (
                SELECT row_number() OVER ()::int AS id, q.*
                FROM (
                    -- Học viên tham gia: mỗi lượt Ghi danh chưa hủy tính 1
                    SELECT
                        en.course_id AS course_id,
                        en.class_id AS class_id,
                        en.date_enroll AS date,
                        'participant' AS metric_type,
                        1 AS count_value,
                        0::numeric AS amount_value,
                        (SELECT currency_id FROM res_company ORDER BY id LIMIT 1) AS currency_id
                    FROM academic_enrollment en
                    WHERE en.state != 'cancel'

                    UNION ALL

                    -- Hoàn thành
                    SELECT
                        en.course_id,
                        en.class_id,
                        en.date_enroll,
                        'completed',
                        1,
                        0::numeric,
                        (SELECT currency_id FROM res_company ORDER BY id LIMIT 1)
                    FROM academic_enrollment en
                    WHERE en.state = 'completed'

                    UNION ALL

                    -- Người phụng sự: mỗi dòng trong bảng quan hệ Lớp học <-> Liên hệ
                    -- = 1 người được phân công phụng sự 1 lớp. Không có field ngày
                    -- riêng cho việc phân công này nên tạm lấy ngày bắt đầu dự kiến
                    -- của Đợt học, không có thì lấy ngày tạo Lớp học.
                    SELECT
                        cls.course_id,
                        cls.id,
                        COALESCE(intk.date_start, cls.create_date::date),
                        'volunteer',
                        1,
                        0::numeric,
                        (SELECT currency_id FROM res_company ORDER BY id LIMIT 1)
                    FROM academic_class_volunteer_rel rel
                    JOIN academic_class cls ON cls.id = rel.class_id
                    LEFT JOIN academic_intake intk ON intk.id = cls.intake_id

                    UNION ALL

                    -- Gieo hạt: mỗi dòng hóa đơn bán hàng ĐÃ THANH TOÁN dùng đúng Sản
                    -- phẩm được đánh dấu "Là sản phẩm Gieo hạt" (is_donation_product) -
                    -- số tiền tự do do Sale/Kế toán tự nhập trên dòng hóa đơn, không có
                    -- giá niêm yết cố định như học phí. Lớp học ưu tiên lấy trực tiếp từ
                    -- cột "Lớp học" ngay trên dòng hóa đơn (aml.class_id - Kế toán tự
                    -- chọn khi ghi hóa đơn tay, không qua Đơn hàng), nếu trống mới lấy
                    -- qua dòng Đơn hàng gốc (sol.class_id). Cả 2 đều trống nghĩa là
                    -- khoản ủng hộ chung, không thuộc riêng khóa/lớp nào.
                    SELECT
                        cls.course_id,
                        cls.id,
                        am.invoice_date,
                        'donation',
                        1,
                        aml.price_subtotal,
                        am.currency_id
                    FROM account_move_line aml
                    JOIN account_move am ON am.id = aml.move_id
                    JOIN product_product pp ON pp.id = aml.product_id
                    JOIN product_template pt ON pt.id = pp.product_tmpl_id AND pt.is_donation_product = true
                    LEFT JOIN sale_order_line_invoice_rel rel3 ON rel3.invoice_line_id = aml.id
                    LEFT JOIN sale_order_line sol ON sol.id = rel3.order_line_id
                    LEFT JOIN academic_class cls ON cls.id = COALESCE(aml.class_id, sol.class_id)
                    WHERE am.move_type = 'out_invoice'
                      AND am.state = 'posted'
                      AND am.payment_state IN ('paid', 'in_payment')

                    UNION ALL

                    -- Thu (học phí): mỗi dòng hóa đơn bán hàng ĐÃ THANH TOÁN, sản phẩm
                    -- khớp đúng Sản phẩm liên kết của 1 Khóa học nào đó. Lấy tiền trước
                    -- thuế (price_subtotal) vì thuế GTGT thu hộ không phải doanh thu
                    -- thật của Seroto. Lớp học ưu tiên lấy trực tiếp từ cột "Lớp học"
                    -- trên dòng hóa đơn (aml.class_id), nếu trống mới lấy qua dòng đơn
                    -- hàng gốc đã sinh ra đúng dòng hóa đơn này (sale_order_line_invoice_rel)
                    -- - LEFT JOIN vì hóa đơn tạo tay không qua đơn hàng vẫn cần hiện.
                    SELECT
                        course.id,
                        COALESCE(aml.class_id, sol.class_id),
                        am.invoice_date,
                        'revenue',
                        1,
                        aml.price_subtotal,
                        am.currency_id
                    FROM account_move_line aml
                    JOIN account_move am ON am.id = aml.move_id
                    JOIN product_product pp ON pp.id = aml.product_id
                    JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    JOIN academic_course course ON course.product_id = pt.id
                    LEFT JOIN sale_order_line_invoice_rel rel2 ON rel2.invoice_line_id = aml.id
                    LEFT JOIN sale_order_line sol ON sol.id = rel2.order_line_id
                    WHERE am.move_type = 'out_invoice'
                      AND am.state = 'posted'
                      AND am.payment_state IN ('paid', 'in_payment')

                    UNION ALL

                    -- Hoàn tiền: hóa đơn điều chỉnh giảm (out_refund) đã ghi sổ và đã
                    -- tất toán - trừ THẲNG vào cùng loại "revenue" (số âm) để "Thu" tự
                    -- ra đúng số thực nhận, không cần người xem tự cộng trừ tay.
                    SELECT
                        course.id,
                        COALESCE(aml.class_id, sol.class_id),
                        am.invoice_date,
                        'revenue',
                        1,
                        -aml.price_subtotal,
                        am.currency_id
                    FROM account_move_line aml
                    JOIN account_move am ON am.id = aml.move_id
                    JOIN product_product pp ON pp.id = aml.product_id
                    JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    JOIN academic_course course ON course.product_id = pt.id
                    LEFT JOIN sale_order_line_invoice_rel rel2 ON rel2.invoice_line_id = aml.id
                    LEFT JOIN sale_order_line sol ON sol.id = rel2.order_line_id
                    WHERE am.move_type = 'out_refund'
                      AND am.state = 'posted'
                      AND am.payment_state IN ('paid', 'in_payment')

                    UNION ALL

                    -- Chi: hóa đơn nhà cung cấp (in_invoice) đã ghi sổ và đã thanh toán,
                    -- gắn đúng field "Lớp học" (aml.class_id) trên dòng hóa đơn - field
                    -- riêng của module này, KHÔNG dùng Kế toán phân tích chuẩn của Odoo
                    -- (giao diện đó chỉ có ở app Kế toán Enterprise, không có trong
                    -- Invoicing Community). Chi phí không gắn Lớp học nào (chi phí
                    -- chung/ngoài phạm vi) sẽ không có dòng nào khớp, tự động không xuất
                    -- hiện trong báo cáo.
                    SELECT
                        cls.course_id,
                        cls.id,
                        am.invoice_date,
                        'expense',
                        1,
                        aml.price_subtotal,
                        am.currency_id
                    FROM account_move_line aml
                    JOIN account_move am ON am.id = aml.move_id
                    JOIN academic_class cls ON cls.id = aml.class_id
                    WHERE am.move_type = 'in_invoice'
                      AND am.state = 'posted'
                      AND am.payment_state IN ('paid', 'in_payment')
                ) q
            )
        """)
