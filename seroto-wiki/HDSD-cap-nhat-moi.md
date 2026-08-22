# HDSD — Nội dung mới cập nhật

Chỉ gồm phần **thay đổi/bổ sung mới** so với 7 trang đã có sẵn trên Wiki.js — không lặp lại nội dung cũ. Mỗi mục có ghi rõ **đây là trang mới hoàn toàn hay là nội dung chèn thêm vào trang đã có**, để tiện ghép vào Wiki.js sau khi bạn duyệt xong.

---

## A. 4 TRANG HOÀN TOÀN MỚI

### A.1 Người phụng sự (Angelina)

*Trang mới, đề xuất đặt cạnh trang "3. Quản lý lớp, quản lý học viên".*

**Dành cho:** Quản lý (Phase 1 — chỉ nội bộ tra cứu)

"Angelina" là tên gọi nội bộ cho vai trò **tình nguyện viên không lương**, hỗ trợ vài việc nhỏ cho Ban tổ chức — **không phải** thành viên chính thức của Ban tổ chức.

**Cách gán:** Trên form Lớp học, thêm người vào field **"Người phụng sự"** (tách biệt hoàn toàn khỏi "Ban tổ chức").

**Tra cứu:** Menu **Đào tạo › Học viên & Nhân Sự › Người phụng sự** — danh sách tự động gồm mọi người đã từng được gán ở bất kỳ lớp nào, hiển thị: email, sđt, ngày sinh, địa chỉ, "Đang học"/"Đã học" (nếu người đó cũng từng là học viên), "Đã phụng sự" (những lớp đã hỗ trợ).

**Lưu ý quan trọng — Phase 1:** Người phụng sự **hiện chưa có tài khoản đăng nhập vào phần mềm** — hoàn toàn chỉ là dữ liệu để nội bộ tra cứu, không có rủi ro họ nhìn thấy dữ liệu khách hàng/học viên. Nếu sau này cần cấp quyền đăng nhập cho chính họ (Phase 2), sẽ làm thêm ở bước riêng, không cần sửa lại dữ liệu Phase 1 này.

---

### A.2 Gieo hạt

*Trang mới, đề xuất đặt sau trang "2. Đăng ký vào lớp học".*

**Dành cho:** Sale, Kế toán

Khoản tiền **tự nguyện, không có mức quy định trước** mà học viên (hoặc bất kỳ cá nhân/tổ chức nào khác) gửi Seroto. **Đi qua đúng luồng Đơn hàng/Hóa đơn quen thuộc** — giống hệt cách ghi nhận học phí "Thu", chỉ khác ở chỗ dùng riêng 1 Sản phẩm tên **"Gieo hạt"** (giá để 0đ mặc định vì mỗi khoản một số tiền khác nhau).

**Cách ghi nhận:**
1. Lên Đơn hàng — chọn Khách hàng là người/tổ chức gửi (hoặc tạo thẳng Hóa đơn, **không bắt buộc** phải qua Đơn hàng).
2. Thêm dòng sản phẩm **"Gieo hạt"**, sửa giá = đúng số tiền ủng hộ.
3. *(Tùy chọn)* chọn **Lớp học** ngay trên dòng sản phẩm/dòng hóa đơn đó nếu muốn khoản này tính riêng cho 1 lớp cụ thể trong Báo cáo tổng hợp — để trống nếu là ủng hộ chung, không thuộc khóa/lớp nào.
4. Xác nhận đơn hàng → Tạo hóa đơn → Đăng ký thanh toán (y hệt quy trình ghi nhận học phí, không có bước nào khác lạ).

**Vì sao không có menu/form riêng?** Bản đầu đã thử làm 1 model riêng (có lúc còn thêm cả "Phiếu thu" kế toán độc lập) nhưng đòi hỏi hiểu thêm về Sổ nhật ký/chứng từ kế toán — không phù hợp vì phần mềm chỉ cài Hóa đơn (Invoicing) Community, không có app Kế toán đầy đủ. Chuyển hẳn sang tái dùng luồng Đơn hàng/Hóa đơn sẵn có giúp Sale/Kế toán không phải học thêm quy trình mới.

**Gieo hạt khác "Thu" (học phí) ở điểm nào?** Cùng đi qua Đơn hàng/Hóa đơn như nhau, khác ở: (1) dùng sản phẩm riêng "Gieo hạt" thay vì sản phẩm của từng khóa học, (2) giá tự nhập mỗi lần, không có giá niêm yết cố định, (3) không bắt buộc gắn Khóa học/Lớp học.

---

### A.3 Báo cáo tổng hợp

*Trang mới, đề xuất đặt cuối cùng (sau "Giải thích thêm").*

**Dành cho:** Quản lý

Menu **Đào tạo › Báo cáo & Cấu hình › Báo cáo tổng hợp** — gộp **6 loại số liệu** về 1 màn hình Pivot duy nhất, không cần mở nhiều menu rồi tự cộng tay.

| Loại số liệu | Nguồn |
|---|---|
| Học viên tham gia | Ghi danh (mọi trạng thái trừ Đã hủy) |
| Hoàn thành | Ghi danh trạng thái Hoàn thành |
| Người phụng sự | Field "Người phụng sự" trên Lớp học |
| Gieo hạt | Hóa đơn bán hàng đã thanh toán, dùng đúng sản phẩm "Gieo hạt" |
| Thu (học phí) | Hóa đơn bán hàng đã thanh toán, trừ thuế GTGT, tự trừ hoàn tiền nếu có |
| Chi | Hóa đơn nhà cung cấp đã thanh toán, chọn đúng Lớp học ngay trên dòng hóa đơn |

**Cách xem:** Mở lên mặc định là Pivot: hàng = Khóa học → Lớp học (bấm mở rộng ra xem từng lớp), cột = Tháng (bấm mở rộng xem theo Loại số liệu). Có thể đổi sang xem theo Năm, hoặc lọc riêng 1 loại số liệu qua ô tìm kiếm.

**Lưu ý về độ đầy đủ:**
- **Chi phí chung/ngoài phạm vi khóa-lớp** (VD thuê văn phòng) — để trống Lớp học trên dòng hóa đơn, khoản đó sẽ **không** xuất hiện trong báo cáo này (đúng chủ đích).
- **"Thu"/"Gieo hạt" tách theo Lớp học**: ưu tiên lấy từ cột "Lớp học" chọn trực tiếp trên dòng hóa đơn; nếu trống mới lấy qua dòng Đơn hàng gốc (khi hóa đơn được tạo từ Đơn hàng có chọn Lớp học ở dòng sản phẩm) — để trống cả 2 nơi thì không tách được theo lớp, vẫn cộng đúng vào tổng chung.
- **"Người phụng sự"** lấy mốc thời gian theo ngày bắt đầu dự kiến của đợt học (không có field ngày riêng cho việc phân công phụng sự).

---

### A.4 Tự động hóa: Đăng ký + Thanh toán trên Website

*Trang mới, đề xuất đặt ngay sau trang "2. Đăng ký vào lớp học" (thay thế phần mô tả thao tác thủ công cũ ở Tình huống đăng ký online).*

**Dành cho:** Sale, Kế toán, Quản lý

**Trước đây:** khách đăng ký + thanh toán xong, **Sale vẫn phải vào backend bấm tay** từng bước — Xác nhận phiếu đăng ký → Tạo đơn hàng → Xác nhận đơn hàng → Tạo hóa đơn → Đăng ký thanh toán — thì học viên mới thực sự được ghi danh vào lớp.

**Giờ đây:** website đã nối cổng thanh toán **payOS thật** (quét QR/chuyển khoản ngân hàng thật, không còn giả lập) — ngay khi payOS báo đã nhận tiền, hệ thống **tự động làm hết** chuỗi trên trong 1 lần: Đơn hàng, Hóa đơn, Đăng ký thanh toán, Ghi danh vào lớp đều xong ngay lập tức, Sale không cần thao tác gì cho lượt đăng ký đó nữa.

Trả lời **"Câu hỏi chuyên sâu"** (tab 3 của form đăng ký) **không phải điều kiện** cho việc tự động này — khách có thể điền trước hoặc sau khi đã được ghi danh, không ảnh hưởng gì tới việc vào lớp.

**Mỗi phiếu đăng ký giờ có 1 Mã phiếu riêng** (VD "PDK8") hiện ngay trên đầu form — dùng để tra cứu nhanh (gõ thẳng mã vào ô tìm kiếm chung là ra đúng phiếu) và đối chiếu với nội dung chuyển khoản khách hàng thực hiện.

**Sale vẫn cần làm gì?**
- Theo dõi bộ lọc **"Cần xử lý"** ở menu Phiếu đăng ký để chủ động nhắc khách điền nốt Câu hỏi chuyên sâu nếu còn thiếu.
- Nếu 1 phiếu nào đó tự động hóa bị lỗi giữa chừng (VD sản phẩm chưa gắn giá) — phiếu vẫn hiện đúng trạng thái **"Đã thanh toán"** nhưng chưa có Đơn hàng đi kèm; Sale bấm nút **"Tạo đơn hàng"** thủ công như quy trình cũ để xử lý tiếp (cơ chế dự phòng, không mất dữ liệu thanh toán đã ghi nhận).

**Kế toán:**
- Trên form Phiếu đăng ký có field **"Phiếu thu"** — trỏ thẳng tới đúng chứng từ kế toán hệ thống tự tạo.
- Trên form Phiếu đăng ký cũng có field **"Giao dịch payOS"** — mở ra xem link/QR thanh toán, trạng thái, và (sau khi đã thanh toán) đầy đủ thông tin đối soát ngân hàng thật: tên/số tài khoản người chuyển, ngân hàng, mã tham chiếu giao dịch, nội dung chuyển khoản ngân hàng thực sự ghi nhận. Màn hình này **chỉ xem, không sửa/tạo tay được** — đảm bảo dữ liệu luôn khớp đúng với payOS.

---

## B. NỘI DUNG CHÈN THÊM VÀO TRANG ĐÃ CÓ

### B.1 Chèn vào trang "1. Mở khóa học, mở đợt học mới" — cập nhật mục 1.4

> ~~Khi bấm "Mở đợt học" ở bước 3, hệ thống tự tạo luôn Mã phân tích chi phí cho lớp mới~~ — **đã bỏ hẳn**, không còn khái niệm "Mã phân tích chi phí" trong phần mềm nữa (chỉ có ở app Kế toán Enterprise, không có trong Invoicing Community đang dùng). Về sau khi phát sinh chi phí cho lớp này, Kế toán chỉ cần chọn thẳng **Lớp học** ngay trên dòng hóa đơn nhà cung cấp lúc ghi hóa đơn (xem trang "Báo cáo tổng hợp") — không cần thiết lập/tạo mã gì trước ở bước mở đợt học này.

### B.2 Chèn vào trang "3. Quản lý lớp, quản lý học viên" — cập nhật mục 3.1

Form Lớp học có 3 nhóm nhân sự **tách biệt hoàn toàn**, không dùng lẫn nhau:

| Field | Vai trò | Ghi chú |
|---|---|---|
| Giảng viên | Người trực tiếp đứng lớp | Chỉ chọn được người đã tick "Là giảng viên" |
| Ban tổ chức | Thành viên chính thức hỗ trợ vận hành | — |
| **Người phụng sự** | Hỗ trợ vài việc nhỏ, không phải thành viên chính | Xem trang "Người phụng sự (Angelina)" |

Việc gắn chi phí cho lớp (để tính "Chi" ở Báo cáo tổng hợp) **không làm trên form Lớp học** — không còn field/nút nào kiểu "Mã phân tích chi phí" ở đây nữa. Kế toán chọn trực tiếp **Lớp học** ngay trên dòng hóa đơn nhà cung cấp lúc ghi nhận chi phí (xem trang "Báo cáo tổng hợp").

### B.3 Chèn vào trang "3. Quản lý lớp, quản lý học viên" — cập nhật mục 3.2 (Buổi học và điểm danh)

Khi tạo buổi học, chọn thêm **phân loại buổi học** (`Zoom` hoặc `BTH`, mặc định Zoom).

Tiến độ học của mỗi học viên (menu Ghi danh) giờ hiện **tách riêng**: "Số buổi đã học" (tổng), **"Điểm danh Zoom"**, **"Điểm danh BTH"** — 3 con số độc lập, không gộp chung nữa.

### B.4 Chèn vào trang "3. Quản lý lớp, quản lý học viên" — cập nhật mục 3.3 (Ghi danh)

Menu **Ghi danh** giờ có sẵn bộ lọc theo 5 trạng thái (Chờ thanh toán/Đã ghi danh/Bảo lưu/Hoàn thành/Đã hủy) và **Nhóm theo Lớp học** ở ô tìm kiếm (mặc định mở lên không lọc/nhóm gì, tự bấm khi cần).

### B.5 Chèn vào trang "3. Quản lý lớp, quản lý học viên" — cập nhật mục 3.4 (Hồ sơ Học viên)

Hồ sơ Học viên (và cả màn hình Danh bạ/CRM thường) giờ hiện thêm 2 field **"Đang học"** / **"Đã học"** (dạng thẻ) — tự tính từ Ghi danh ("Đang học" = Ghi danh trạng thái "Đã ghi danh"), xem được ở bất kỳ đâu có hồ sơ Liên hệ đó, không riêng gì menu Học viên. Đây cũng chính là dữ liệu CRM dùng để tra "khách này đã học khóa nào, khóa nào chưa hoàn thành".

### B.6 Chèn vào trang "5. Giải thích thêm về phần mềm" — mục mới 5.7

**"Gieo hạt" khác "Thu" (học phí) thế nào?** Cả 2 đều đi qua Đơn hàng/Hóa đơn **giống hệt nhau** — khác ở Sản phẩm dùng (mỗi khóa học có 1 sản phẩm học phí riêng, còn "Gieo hạt" dùng chung 1 sản phẩm cho mọi khoản ủng hộ) và Gieo hạt giá tự nhập mỗi lần thay vì giá niêm yết cố định, không bắt buộc gắn Khóa học/Lớp học.

### B.7 Chèn vào trang "5. Giải thích thêm về phần mềm" — cập nhật mục 5.6 (Liên hệ quan hệ thế nào)

Bổ sung thêm 1 dòng vào bảng vai trò đã có:

| Vai trò | Cách xác định |
|---|---|
| Người phụng sự | Được chọn vào field "Người phụng sự" của 1 Lớp học |

### B.8 Chèn vào trang "1. Mở khóa học, mở đợt học mới" — Khu vực hiển thị trên website

Field **"Đối tượng"** trên form Khóa học đã đổi tên thành **"Khu vực hiển thị"** và chuyển ra **tab riêng cùng tên** trong notebook (trước đây là ô tag gọn nằm trong nhóm "Thông tin chung"). Tab hiện dạng **bảng đầy đủ 2 cột** — Tên khu vực và Mã khu vực — dễ tra đúng mã cần nhập khi cấu hình snippet trên website (ô "Mã khu vực hiển thị" ở panel Tùy chỉnh của snippet "Khóa học - Khu vực hiển thị"). Menu quản lý danh sách khu vực cũng đổi tên tương ứng, nay nằm ở **Đào tạo › Báo cáo & Cấu hình › Khu vực hiển thị trên website**.

### B.9 Chèn vào đầu tài liệu (hoặc mục điều hướng chung) — Cấu trúc menu "Đào tạo" đã gọn lại

Menu **Đào tạo** trước đây liệt kê phẳng hơn 10 mục ngang hàng, giờ gộp lại thành **4 nhóm** cho gọn và đúng luồng nghiệp vụ:

| Nhóm | Gồm |
|---|---|
| **Khóa học** | Khóa học, Đợt học, Lớp học |
| **Tuyển sinh & Vận hành** | Phiếu đăng ký, Ghi danh, Điểm danh, Chứng chỉ (đúng thứ tự vòng đời 1 học viên đi qua) |
| **Học viên & Nhân Sự** | Học viên, Giảng viên, Người phụng sự |
| **Báo cáo & Cấu hình** | Báo cáo tổng hợp, Khu vực hiển thị trên website |

Chỉ đổi vị trí menu, không đổi bất kỳ màn hình/thao tác nào bên trong từng mục.

### B.10 Chèn vào trang "3. Quản lý lớp, quản lý học viên" — Chứng chỉ

- Màn hình danh sách **Chứng chỉ** đã **ẩn nút "Mới"** — chứng chỉ **chỉ được cấp** qua nút **"Hoàn thành & Cấp chứng chỉ"** trên form Ghi danh, không tạo tay trực tiếp ở danh sách Chứng chỉ được nữa (tránh chứng chỉ không gắn đúng 1 lượt Ghi danh thật nào).
- Form Ghi danh giờ có nút thông minh **"Chứng chỉ"** trong khung nút phía trên (chỉ hiện khi đã cấp) — bấm mở thẳng đúng chứng chỉ tương ứng. Ngược lại, form Chứng chỉ cũng hiện field **"Ghi danh"** trỏ về đúng lượt ghi danh đã sinh ra nó — tra cứu 2 chiều đều được.
- Hệ thống tự chặn cấp trùng — 1 lượt Ghi danh chỉ có tối đa 1 Chứng chỉ dù bấm "Hoàn thành" nhiều lần.

### B.11 Chèn vào đầu tài liệu (hoặc mục điều hướng chung) — Menu "payOS"

Menu riêng **payOS** (chỉ **Quản trị hệ thống** thấy được, không phải mọi nhân viên) gồm 2 mục:
- **Giao dịch** — danh sách toàn bộ giao dịch thanh toán payOS đã tạo (đúng nội dung đã mô tả ở mục A.4), bấm vào menu cha "payOS" sẽ vào thẳng đây.
- **Cấu hình** — nơi nhập 3 khóa kết nối với tài khoản payOS của tổ chức (chỉ làm 1 lần lúc thiết lập, không cần đụng tới sau đó trừ khi đổi khóa).

---

## Việc còn treo (chưa làm, không nằm trong phần cập nhật này)

- CRM tổng hợp **chưa** gồm các lượt đăng ký web bị từ chối/hủy/chưa xử lý xong (đã đề xuất hướng giải quyết, chưa triển khai).
- "Chi phí chung" (không gắn khóa/lớp nào) chưa có chỗ theo dõi riêng — chủ đích để ngoài phạm vi Báo cáo tổng hợp.
- Đã có sẵn cơ chế chặn không cho đăng sản phẩm học phí/Gieo hạt lên khu vực bán hàng công khai (Shop) nếu tổ chức có mở rộng thêm chức năng này sau này — hiện chưa có Shop nên chưa có gì để thao tác.
