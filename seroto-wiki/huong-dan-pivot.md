# Hướng dẫn tinh chỉnh bảng Pivot (Báo cáo tổng hợp)

Áp dụng cho mọi màn hình xem dạng **Pivot** trong phần mềm (mặc định gặp ở menu **Đào tạo › Báo cáo & Cấu hình › Báo cáo tổng hợp**, nhưng cách thao tác giống hệt ở bất kỳ Pivot nào khác trong hệ thống).

---

## 1. Cấu trúc màn hình Pivot

- **Hàng** (bên trái): mặc định nhóm theo Khóa học → Lớp học.
- **Cột** (phía trên): mặc định nhóm theo Tháng.
- **Đo lường**: mỗi ô giao giữa 1 hàng và 1 cột hiện ra 1 hoặc nhiều con số (VD "Số lượng", "Số tiền").
- Ô có dấu **+** (mở rộng) hoặc **-** (thu gọn) ở đầu dòng/cột — bấm để đào sâu thêm 1 cấp hoặc gom lại.

## 2. Mở rộng / thu gọn để xem chi tiết hơn

- Bấm dấu **+** cạnh 1 dòng (VD "Khóa học") → chọn tiêu chí muốn đào sâu tiếp (VD "Lớp học") → bảng tự thêm 1 cấp con dưới dòng đó.
- Muốn thu gọn lại, bấm dấu **-** ở đúng dòng/cột đó.
- Làm tương tự với **cột** phía trên (VD từ "Tháng" đào sâu tiếp xuống "Loại số liệu").
- Có thể đào sâu **nhiều cấp cùng lúc**, mỗi dòng/cột chọn tiêu chí đào sâu khác nhau nếu muốn so sánh nhiều chiều.

## 3. Thêm/bớt số liệu hiển thị (Đo lường)

- Bấm nút **"Chỉ số"** (góc trên bên trái bảng) → hiện danh sách các con số có thể xem (VD "Số lượng", "Số tiền").
- Tick/bỏ tick để hiện/ẩn từng loại — hữu ích khi 1 loại số liệu không có ý nghĩa với dòng đang xem (VD "Số tiền" luôn bằng 0 ở "Học viên tham gia"/"Hoàn thành" vì đây là số liệu đếm lượt, không phải tiền).

## 4. Đảo chiều Hàng ↔ Cột

- Bấm nút **mũi tên 2 chiều** (cạnh nút "Chỉ số") để hoán đổi toàn bộ nội dung đang xếp theo Hàng sang Cột và ngược lại — hữu ích khi muốn nhìn theo chiều khác mà không phải dựng lại từ đầu.

## 5. Lọc dữ liệu trước khi xem

- Gõ trực tiếp vào ô tìm kiếm phía trên (VD tên khóa học, lớp học) rồi Enter — bảng tự lọc lại chỉ còn dữ liệu khớp.
- Bấm mũi tên nhỏ cạnh ô tìm kiếm để mở khung **Bộ lọc / Nhóm theo** có sẵn (VD lọc riêng "Thu (học phí)", nhóm theo "Lớp học") — tick nhiều mục cùng lúc để kết hợp điều kiện.
- Có thể xóa từng điều kiện lọc bằng nút **x** trên thẻ lọc đang hiện, hoặc xóa hết để xem lại toàn bộ dữ liệu.

## 6. Sắp xếp lại theo giá trị

- Bấm trực tiếp vào tiêu đề 1 cột số (VD "Số tiền") — bảng tự sắp xếp các dòng từ cao xuống thấp (hoặc ngược lại) theo đúng cột vừa bấm, tiện tìm nhanh khóa/lớp có Thu/Chi cao nhất.

## 7. Xuất ra Excel

- Bấm nút **hình mũi tên tải xuống** (cạnh nút "Chỉ số") — tải về đúng bảng đang hiển thị trên màn hình (kể cả các cấp đã mở rộng/thu gọn, bộ lọc đang áp dụng) dưới dạng file Excel để lưu trữ hoặc chỉnh sửa thêm.

## 8. Lưu lại cách xem để dùng lại sau

- Sau khi đã chỉnh xong (đào sâu đúng cấp, lọc đúng điều kiện muốn) — bấm mũi tên cạnh ô tìm kiếm → mục **"Bộ lọc đã lưu"** → đặt tên → Lưu.
- Lần sau vào lại đúng màn hình đó, chỉ cần chọn lại đúng bộ lọc đã lưu trong danh sách, không cần tinh chỉnh lại từ đầu. Có thể đặt 1 bộ lọc làm **mặc định** để mỗi lần mở màn hình đều tự áp dụng luôn.

---

**Mẹo nhanh:** muốn xem "khóa nào đang lãi nhất tháng này" — đào sâu Hàng theo Khóa học, lọc riêng 2 loại số liệu "Thu (học phí)" và "Chi", bấm vào tiêu đề cột "Số tiền" để sắp xếp giảm dần.
