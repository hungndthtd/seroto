# HDSD phần mềm Seroto

Sổ tay sử dụng phần mềm quản lý khóa học / lớp học / đăng ký / báo cáo của Seroto — viết cho 3 nhóm người dùng: **Sale**, **Kế toán**, **Quản lý (website, khóa học, lớp học)**.

> Bản cập nhật — gộp toàn bộ nội dung đã có trên Wiki.js trước đây và bổ sung các phần mới: Người phụng sự, Gieo hạt, Báo cáo tổng hợp, điểm danh Zoom/BTH, gắn Lớp học trên hóa đơn để tính Chi, tự động hóa đăng ký + thanh toán trên website qua **payOS thật**, gộp bước Xác nhận + Tạo đơn hàng, Mã phiếu tra cứu, Khu vực hiển thị trên website, gộp gọn menu Đào tạo, liên kết Chứng chỉ với Ghi danh. Xem trước ở đây, khi ổn sẽ đẩy lên Wiki.js.

## Mục lục

| Phần | Nội dung |
|---|---|
| 0 | Nhân sự tham gia phần mềm |
| 1 | Mở khóa học, mở đợt học mới |
| 2 | Đăng ký vào lớp học |
| 3 | Quản lý lớp, quản lý học viên |
| 4 | Người phụng sự (Angelina) |
| 5 | Gieo hạt |
| 6 | Báo cáo tổng hợp |
| 7 | Chức năng khác hỗ trợ sử dụng |
| 8 | Giải thích thêm về phần mềm |

**Ngoài phạm vi tài liệu này:** khách đăng ký qua Zalo/Facebook hiện xử lý qua quy trình CRM (Lead/Cơ hội) thông thường, chưa đi qua Phiếu đăng ký ở Phần 2.

---

## 0. Nhân sự tham gia phần mềm

### Sale — Tư vấn / Chăm sóc khách hàng
Với khách đăng ký qua website và thanh toán thành công, hệ thống **tự động xử lý hết** (xem mục 2) — Sale chỉ cần theo dõi, nhắc khách hoàn thiện thông tin còn thiếu. Với khách đăng ký qua điện thoại/Zalo hoặc trường hợp cần xử lý tay, Sale tiếp nhận **Phiếu đăng ký**: xác nhận, từ chối, tạo đơn hàng. Theo dõi trạng thái ghi danh của học viên mình phụ trách.
- Menu: Phiếu đăng ký, Ghi danh, Học viên, Bán hàng (Đơn hàng)
- Xem được Khóa học/Lớp học nhưng không sửa được

### Kế toán — Hóa đơn & thanh toán
Với khách đăng ký online, hóa đơn/thanh toán/ghi danh đã tự động xử lý xong (xem mục 2) — Kế toán chủ yếu xuất hóa đơn và ghi nhận thanh toán cho các đơn hàng phát sinh ngoài luồng online (điện thoại/Zalo) hoặc khi cần xử lý tay tiếp 1 phiếu bị lỗi tự động. Thao tác này vẫn là bước kích hoạt: hệ thống tự ghi danh học viên, tự đóng Phiếu đăng ký, và tự liên kết **Phiếu thu** vào phiếu ngay khi hoàn tất — dù thanh toán qua payOS hay ghi nhận thủ công (tiền mặt, chuyển khoản kênh khác) đều tự động như nhau, không phân biệt. Kế toán cũng là người ghi hóa đơn nhà cung cấp và chọn Lớp học trên dòng hóa đơn để tính "Chi" theo lớp, cũng như ghi nhận khoản "Gieo hạt" khi có người ủng hộ, và có thể tra cứu đối soát ngân hàng thật qua field "Giao dịch payOS" trên mỗi phiếu (xem mục 2).
- Menu: Bán hàng > Đơn hàng, Kế toán > Hóa đơn (bán hàng & nhà cung cấp)

### Quản lý — Website, khóa học, lớp học
Toàn quyền tạo khóa học, mở đợt học mới, quản lý lớp/giáo viên/buổi học, xem Báo cáo tổng hợp.
- Menu: toàn bộ mục Đào tạo
- Có toàn bộ quyền của Sale, cộng thêm quyền chỉnh sửa Khóa học/Lớp học/Đợt học

---

## 1. Thiết lập thông tin khóa học, mở khóa học mới

**Dành cho:** Quản lý

### 1.1 Tạo khóa học mới
Vào **Đào tạo › Khóa học › Mới**.

| Trường thông tin | Bắt buộc | Ghi chú |
|---|---|---|
| Tên khóa học, Mã khóa học | Có | Mã hiển thị trước tên trong mọi ô chọn khóa học |
| Slogan, Mô tả, Hình thức học, Giảng viên/Cố vấn | Không | Hiển thị trên thẻ khóa học ở website |
| Sản phẩm liên kết | **Có** | Bắt buộc — không có sản phẩm thì không thể lên đơn hàng/hóa đơn (xem mục 8.1) |

### 1.2 Cấu hình câu hỏi chuyên sâu
Tab **Câu hỏi chuyên sâu** — bộ câu hỏi khách trả lời ở bước 3 form đăng ký web. Mỗi khóa học 1 bộ riêng.

### 1.3 Thông tin hiển thị trên website
| Field | Bản chất | Tác dụng |
|---|---|---|
| Đợt tuyển sinh, Ngày học, Giờ học, Thời hạn đăng ký | Chữ tự do | Chỉ để **hiển thị** |
| Ngày mở đăng ký, Ngày đóng đăng ký | Ngày thật | Tự **ẩn/hiện** nút "Đăng ký ngay" trên website |

### 1.4 Mở đợt học mới
Bấm nút **"Mở đợt học mới"** trên form Khóa học:
1. Điền mã đợt (VD `K19`), ngày bắt đầu/kết thúc dự kiến, chọn giáo viên.
2. Tick "Đặt làm lớp nhận đăng ký" nếu muốn.
3. Bấm "Mở đợt học" — hệ thống tự tạo Đợt học + Lớp học (trạng thái **Sắp mở**).

### 1.5 Vòng đời của một Lớp học
| Trạng thái | Bấm nút | Khi nào dùng |
|---|---|---|
| Sắp mở | — | Mặc định sau khi mở đợt |
| Đang nhận đăng ký | Mở đăng ký | Sẵn sàng nhận khách; điều kiện để lớp xuất hiện ở "Lớp nhận đăng ký" |
| Đã đóng đăng ký | Đóng đăng ký | Đủ chỉ tiêu/hết hạn |
| Đang học | Bắt đầu học | Lớp đã khai giảng |
| Hoàn thành | Hoàn thành | Lớp đã kết thúc |

### 1.6 "Lớp nhận đăng ký"
Field trên form Khóa học — lớp mà **mọi khách đăng ký mới trên web sẽ tự động được gắn vào**. Nhiều lớp mở song song → Quản lý chủ động đổi field này khi 1 lớp đầy.

### 1.7 Khu vực hiển thị trên website
Tab **"Khu vực hiển thị"** trên form Khóa học — chọn khóa học này xuất hiện ở khu vực nào trên website (VD trang dành cho Giáo viên, trang dành cho Trường học...). Mỗi khu vực có **Tên** và **Mã** riêng — quản lý danh sách khu vực tại **Đào tạo › Báo cáo & Cấu hình › Khu vực hiển thị trên website**. 1 khóa học có thể thuộc nhiều khu vực cùng lúc, hoặc không thuộc khu vực nào nếu chỉ muốn hiển thị chung.

---

## 2. Đăng ký vào lớp học

**Dành cho:** Sale, Kế toán

### Sơ đồ luồng tự động (khách đăng ký + thanh toán qua website)
| # | Ai làm | Thao tác | Kết quả |
|---|---|---|---|
| 1 | Khách hàng | Điền form 3 bước trên web (Tab 1: Thông tin cơ bản) | Phiếu đăng ký: **Mới đăng ký** |
| 2 | Khách hàng | Thanh toán ở Tab 2 qua **payOS** (quét QR/chuyển khoản ngân hàng thật, không còn giả lập) | Hệ thống ghi nhận đã thanh toán |
| 3 | Hệ thống | Tự động: tạo Đơn hàng, xác nhận, xuất Hóa đơn, ghi nhận thanh toán, ghi danh học viên | Ghi danh + Phiếu: **Hoàn tất** |
| — | Khách hàng | Trả lời Câu hỏi chuyên sâu ở Tab 3 (trước hoặc sau khi đã vào lớp đều được) | Không ảnh hưởng tới việc ghi danh |

Bước 3 diễn ra **ngay lập tức** sau khi thanh toán thành công — Sale/Kế toán **không cần thao tác gì** cho các lượt đăng ký online bình thường.

**Mã phiếu:** mỗi Phiếu đăng ký có 1 mã riêng (VD "PDK8") hiện ngay trên đầu form — gõ thẳng mã này vào ô tìm kiếm chung là ra đúng phiếu, tiện đối chiếu khi khách báo đã chuyển khoản.

### 2.1 Khi nào Sale/Kế toán vẫn cần thao tác tay
- **Khách đăng ký qua điện thoại/Zalo** (không qua form web + thanh toán online) — vẫn theo quy trình thủ công như mục 2.2-2.3 bên dưới.
- **Luồng tự động gặp lỗi** (hiếm gặp, VD dữ liệu sản phẩm/giá thiếu sót) — phiếu vẫn hiện đúng trạng thái đã thanh toán nhưng chưa có Đơn hàng đi kèm. Sale bấm nút **"Tạo đơn hàng (khắc phục lỗi)"** xuất hiện trên phiếu để xử lý tiếp.
- Sale nên thường xuyên xem bộ lọc **"Cần xử lý"** ở menu Phiếu đăng ký để chủ động nhắc khách hoàn thiện Câu hỏi chuyên sâu nếu còn thiếu.

### 2.2 Xác nhận Phiếu đăng ký (đăng ký qua điện thoại/Zalo)
**Đào tạo › Tuyển sinh & Vận hành › Phiếu đăng ký** — mặc định lọc "Cần xử lý". Với phiếu **chưa thanh toán**, Sale kiểm tra cột "Đã đầy đủ thông tin" rồi bấm **Xác nhận** hoặc **Từ chối** (nhập lý do).

Bấm **Xác nhận** giờ **tự tạo luôn Đơn hàng** trong cùng 1 lần bấm (không còn phải bấm 2 nút riêng như trước) — hệ thống mở thẳng qua Đơn hàng vừa tạo (đã điền sẵn Khách hàng/Sản phẩm/Lớp học) để Sale kiểm tra rồi tự xác nhận đơn hàng đó. Hồ sơ khách hàng chỉ được tạo thật tại đúng bước Xác nhận này (với luồng tự động qua payOS, hồ sơ được tạo ngay khi hệ thống tự xử lý).

Nếu đổi Khóa học ngay trên phiếu (khi phiếu còn "Nháp"), danh sách **Câu hỏi chuyên sâu** tự cập nhật lại theo đúng khóa học vừa chọn — không cần tự thêm/xóa dòng câu hỏi tay.

Lưu ý: với phiếu **đã thanh toán thành công qua website**, hệ thống đã tự động xử lý xong (ghi danh vào lớp, tạo đơn hàng/hóa đơn) trước khi Sale kịp xem — bấm "Từ chối" lúc này chỉ đổi trạng thái của Phiếu đăng ký, **không** hủy ngược lại Đơn hàng/Ghi danh đã tạo. Muốn hủy thật sự (hoàn tiền, hủy ghi danh) cần xử lý riêng ở Đơn hàng/Ghi danh tương ứng.

### 2.3 Kế toán thanh toán, hệ thống tự ghi danh
Xuất hóa đơn → Ghi nhận thanh toán → hệ thống tự ghi danh học viên, Phiếu tự chuyển **Hoàn tất**, đồng thời tự liên kết **Phiếu thu** vào phiếu (đúng cơ chế mà luồng tự động qua payOS cũng đang dùng lại) — áp dụng như nhau dù thanh toán qua payOS hay Kế toán tự ghi nhận thủ công (tiền mặt, chuyển khoản kênh khác).

Trên form Phiếu đăng ký có 2 field phục vụ đối soát:
- **"Phiếu thu"** — trỏ thẳng tới chứng từ kế toán tương ứng.
- **"Giao dịch payOS"** — chỉ có khi khách thanh toán qua website; mở ra xem link/QR, trạng thái, và (sau khi đã thanh toán) đầy đủ thông tin đối soát ngân hàng thật: tên/số tài khoản người chuyển, ngân hàng, mã tham chiếu giao dịch. Màn hình này **chỉ xem, không sửa/tạo tay được**.

---

## 3. Quản lý lớp, quản lý học viên

**Dành cho:** Sale, Quản lý

### 3.1 Vận hành một lớp học
Form Lớp học có 3 nhóm nhân sự **tách biệt hoàn toàn**, không dùng lẫn nhau:

| Field | Vai trò | Ghi chú |
|---|---|---|
| Giảng viên | Người trực tiếp đứng lớp | Chỉ chọn được người đã tick "Là giảng viên" |
| Ban tổ chức | Thành viên chính thức hỗ trợ vận hành | — |
| **Người phụng sự** | Hỗ trợ vài việc nhỏ, không phải thành viên chính | Xem chi tiết ở Phần 4 |

Việc gắn chi phí cho lớp (để tính "Chi" ở Phần 6) không làm trên form Lớp học — Kế toán chọn trực tiếp Lớp học ngay trên dòng hóa đơn nhà cung cấp lúc ghi chi phí (xem mục 6).

### 3.2 Buổi học và điểm danh
1. Tab "Danh sách Buổi học" — thêm buổi mới: tên, thời gian, **phân loại buổi học** (`Zoom` hoặc `BTH`, mặc định Zoom).
2. Bấm **"Khởi tạo danh sách điểm danh"** (chỉ hiện sau khi đã lưu buổi học).
3. Đánh dấu Có mặt/Đi muộn/Vắng có phép/Vắng không phép.

Tiến độ học của mỗi học viên (menu Ghi danh) giờ hiện **tách riêng**: "Số buổi đã học" (tổng), **"Điểm danh Zoom"**, **"Điểm danh BTH"** — 3 con số độc lập, không gộp chung nữa.

### 3.3 Ghi danh và chứng chỉ
Menu **Ghi danh** — đã có sẵn bộ lọc theo 5 trạng thái (Chờ thanh toán/Đã ghi danh/Bảo lưu/Hoàn thành/Đã hủy) và **Nhóm theo Lớp học** ở ô tìm kiếm (mặc định mở lên không lọc/nhóm gì, tự bấm khi cần).

| Trạng thái | Ý nghĩa |
|---|---|
| Chờ thanh toán | Đơn hàng chưa thanh toán xong |
| Đã ghi danh | Học viên chính thức trong lớp |
| Bảo lưu | Tạm dừng học |
| Hoàn thành | Tự sinh Chứng chỉ (đạt/không đạt theo tiến độ ≥ 50%) |
| Đã hủy | Ngừng theo học hẳn |

Chứng chỉ **chỉ được cấp** qua nút "Hoàn thành & Cấp chứng chỉ" trên form Ghi danh — màn hình danh sách Chứng chỉ không cho tạo tay. Form Ghi danh có nút "Chứng chỉ" (chỉ hiện khi đã cấp) để mở thẳng chứng chỉ tương ứng; ngược lại form Chứng chỉ cũng hiện rõ lượt Ghi danh đã sinh ra nó.

### 3.4 Hồ sơ Học viên và Giảng viên
- **Học viên** — tự nhận diện khi có ≥1 lượt ghi danh. Hồ sơ (và cả màn hình Danh bạ/CRM thường) giờ hiện thêm 2 field **"Đang học"** / **"Đã học"** (dạng thẻ) — tự tính từ Ghi danh, xem được ở bất kỳ đâu có hồ sơ Liên hệ đó, không riêng gì menu Học viên.
- **Giảng viên** — tick "Là giảng viên"; tab "Lớp giảng dạy" tự liệt kê khóa/đợt đã dạy.

---

## 4. Người phụng sự (Angelina)

**Dành cho:** Quản lý (Phase 1 — chỉ nội bộ tra cứu)

"Angelina" là tên gọi nội bộ cho vai trò **tình nguyện viên không lương**, hỗ trợ vài việc nhỏ cho Ban tổ chức — **không phải** thành viên chính thức của Ban tổ chức.

### Cách gán
Trên form Lớp học, thêm người vào field **"Người phụng sự"** (tách biệt hoàn toàn khỏi "Ban tổ chức").

### Tra cứu
Menu **Đào tạo › Học viên & Nhân Sự › Người phụng sự** — danh sách tự động gồm mọi người đã từng được gán ở bất kỳ lớp nào, hiển thị: email, sđt, ngày sinh, địa chỉ, "Đang học"/"Đã học" (nếu người đó cũng từng là học viên), "Đã phụng sự" (những lớp đã hỗ trợ).

### Lưu ý quan trọng — Phase 1
Người phụng sự **hiện chưa có tài khoản đăng nhập vào phần mềm** — hoàn toàn chỉ là dữ liệu để nội bộ tra cứu. Vì vậy không có rủi ro họ nhìn thấy dữ liệu khách hàng/học viên. Nếu sau này cần cấp quyền đăng nhập cho chính họ (Phase 2), sẽ làm thêm ở bước riêng (Cổng thông tin giới hạn hoặc tài khoản nội bộ có phân quyền chặt) — không cần sửa lại phần dữ liệu đã có ở Phase 1 này.

---

## 5. Gieo hạt

**Dành cho:** Sale, Kế toán

Khoản tiền **tự nguyện, không có mức quy định trước** mà học viên (hoặc bất kỳ cá nhân/tổ chức nào khác) gửi Seroto. Ghi nhận theo **đúng quy trình Đơn hàng/Hóa đơn quen thuộc** (giống hệt cách ghi nhận học phí) — chỉ khác ở chỗ dùng riêng 1 sản phẩm tên **"Gieo hạt"**.

### Cách ghi nhận
1. Lên Đơn hàng (hoặc tạo thẳng Hóa đơn, không bắt buộc phải qua Đơn hàng) — chọn Khách hàng là người/tổ chức gửi (tạo mới ngay tại ô chọn nếu chưa có hồ sơ).
2. Thêm dòng sản phẩm **"Gieo hạt"**, sửa giá = đúng số tiền ủng hộ (số tiền tự do, không có giá niêm yết cố định).
3. *(Tùy chọn)* chọn **Lớp học** ngay trên dòng đó nếu muốn khoản này tính riêng cho 1 lớp cụ thể trong Báo cáo tổng hợp — để trống nếu là ủng hộ chung, không thuộc khóa/lớp nào.
4. Xác nhận đơn hàng → Tạo hóa đơn → Đăng ký thanh toán (y hệt quy trình ghi nhận học phí).

### Ví dụ 2 tình huống
- **Học viên** gửi sau khi học xong 1 lớp → chọn Lớp học ngay trên dòng sản phẩm.
- **Người ngoài/tổ chức** ủng hộ chung → để trống Lớp học.

### Xem báo cáo
Xem tổng "Gieo hạt" theo Khóa học × Tháng ngay trong **Báo cáo tổng hợp** (mục 6), không cần cộng tay từ nhiều hóa đơn.

---

## 6. Báo cáo tổng hợp

**Dành cho:** Quản lý

Menu **Đào tạo › Báo cáo & Cấu hình › Báo cáo tổng hợp** — gộp **6 loại số liệu** về 1 màn hình Pivot duy nhất, không cần mở nhiều menu rồi tự cộng tay.

| Loại số liệu | Nguồn |
|---|---|
| Học viên tham gia | Ghi danh (mọi trạng thái trừ Đã hủy) |
| Hoàn thành | Ghi danh trạng thái Hoàn thành |
| Người phụng sự | Field "Người phụng sự" trên Lớp học |
| Gieo hạt | Hóa đơn bán hàng đã thanh toán, dùng đúng sản phẩm "Gieo hạt" |
| Thu (học phí) | Hóa đơn bán hàng đã thanh toán, trừ thuế GTGT, tự trừ hoàn tiền nếu có |
| Chi | Hóa đơn nhà cung cấp đã thanh toán, có chọn Lớp học ngay trên dòng hóa đơn |

### Cách xem
Mở lên mặc định là Pivot: hàng = Khóa học → Lớp học (bấm mở rộng ra xem từng lớp), cột = Tháng (bấm mở rộng xem theo Loại số liệu). Có thể đổi sang xem theo Năm, hoặc lọc riêng 1 loại số liệu qua ô tìm kiếm. Xem thêm hướng dẫn tinh chỉnh Pivot (mở rộng/thu gọn, đổi chỉ số, xuất Excel, lưu cách xem...) ở trang riêng "Hướng dẫn tinh chỉnh bảng Pivot".

Cột "Số tiền" chỉ có ý nghĩa với "Gieo hạt"/"Thu"/"Chi" — 3 loại còn lại (Học viên tham gia/Hoàn thành/Người phụng sự) là số liệu đếm lượt, cột "Số tiền" của chúng luôn là 0đ theo đúng chủ đích, không phải lỗi.

### Cách ghi nhận "Chi" cho đúng lớp
Khi Kế toán ghi hóa đơn nhà cung cấp (Kế toán → Nhà cung cấp → Hóa đơn), trên chính dòng chi phí có sẵn cột **"Lớp học"** — chọn đúng lớp phát sinh chi phí đó (VD thuê hội trường, thù lao giảng viên của lớp K19). Không cần thiết lập gì trước ở form Lớp học — chọn trực tiếp ngay lúc ghi hóa đơn.

### Lưu ý về độ đầy đủ
- **Chi phí chung/ngoài phạm vi khóa-lớp** (VD thuê văn phòng) — để trống cột "Lớp học" trên dòng hóa đơn, khoản đó sẽ **không** xuất hiện trong báo cáo này (đúng chủ đích, tránh lẫn vào chi phí hoạt động đào tạo).
- **"Thu"/"Gieo hạt" tách theo Lớp học**: ưu tiên lấy Lớp học chọn trực tiếp trên dòng hóa đơn; nếu trống mới lấy qua dòng Đơn hàng gốc (khi hóa đơn được tạo từ Đơn hàng có chọn Lớp học ở dòng sản phẩm) — để trống cả 2 nơi thì vẫn tính đúng vào tổng chung, chỉ là không tách được theo lớp.
- **"Người phụng sự"** lấy mốc thời gian theo ngày bắt đầu dự kiến của đợt học (không có field ngày riêng cho việc phân công phụng sự).

---

## 7. Chức năng khác hỗ trợ sử dụng

**Dành cho:** Tất cả

### Hoạt động (Activity)
Gắn được lên Phiếu đăng ký, Lớp học, Ghi danh... để tự nhắc việc. Xem tổng hợp qua biểu tượng đồng hồ trên thanh điều hướng.

### Lịch sử thay đổi (Chatter)
Lớp học, Phiếu đăng ký, Ghi danh đều ghi log mỗi lần đổi trạng thái — ai đổi, lúc nào.

### Bộ lọc và nhóm nhanh
Nhiều danh sách đã có sẵn bộ lọc dùng ngay (Phiếu đăng ký: "Cần xử lý"; Ghi danh: theo 5 trạng thái + nhóm theo Lớp học; Báo cáo tổng hợp: theo khóa/lớp/loại số liệu/tháng/năm).

### Tìm kiếm
Ô tìm kiếm chấp nhận tên, số điện thoại, email, hoặc mã khóa học.

---

## 8. Giải thích thêm về phần mềm

**Dành cho:** Tất cả

### 8.1 Khóa học và Sản phẩm liên kết với nhau thế nào?
**Khóa học** là lớp vỏ nghiệp vụ đào tạo. **Sản phẩm** là thứ thực sự xuất hiện trên đơn hàng/hóa đơn — giá bán nằm ở Sản phẩm, không nằm ở Khóa học.

### 8.2 Khóa học → Đợt học → Lớp học → Buổi học quan hệ ra sao?
Khóa học (không đổi) → Đợt học (VD "K19", mỗi khóa tự đánh số riêng) → Lớp học (1 đợt có thể nhiều lớp song song) → Buổi học (nơi điểm danh, có phân loại Zoom/BTH).

### 8.3 Phiếu đăng ký khác gì CRM (Lead)?
| | Phiếu đăng ký | CRM (Lead) |
|---|---|---|
| Nguồn | Web (form nhiều bước) | Zalo, Facebook, liên hệ ngoài |
| Vòng đời | Nháp → Mới đăng ký → Đã xác nhận → Hoàn tất | Quy trình CRM chuẩn (ngoài phạm vi tài liệu này) |

### 8.4 Vì sao nhiều nơi đều có "trạng thái" nhưng ý nghĩa khác nhau?
Phiếu đăng ký (1 lượt đăng ký), Lớp học (vòng đời vận hành cả lớp), Ghi danh (việc học của 1 học viên trong 1 lớp) — 3 khái niệm độc lập, 1 khách có thể có Phiếu "Hoàn tất" nhưng Ghi danh đang "Bảo lưu".

### 8.5 Cổng thanh toán trên website là thật hay giả lập?
Đã là **payOS thật** — không còn giả lập. Cấu hình kết nối (3 khóa của tài khoản payOS) nằm ở menu riêng **payOS › Cấu hình**, chỉ Quản trị hệ thống thấy/sửa được; menu **payOS › Giao dịch** liệt kê toàn bộ giao dịch thanh toán đã tạo.

### 8.6 Liên hệ (Contact) quan hệ thế nào với Học viên, Giảng viên, Ban tổ chức, Người phụng sự?
Tất cả đều dùng **chung 1 hồ sơ Liên hệ** — không phải danh bạ riêng cho từng vai trò:

| Vai trò | Cách xác định |
|---|---|
| Học viên | Tự động khi có ≥1 Ghi danh |
| Giảng viên | Tick "Là giảng viên" |
| Ban tổ chức | Được chọn vào field "Ban tổ chức" của 1 Lớp học |
| Người phụng sự | Được chọn vào field "Người phụng sự" của 1 Lớp học |
| Khách hàng | Đứng tên trên Đơn hàng/Hóa đơn |

1 người có thể mang nhiều vai trò cùng lúc.

**Ví dụ: phụ huynh đăng ký học cho con** — tạo hồ sơ cho phụ huynh (người trả tiền), tạo hồ sơ riêng cho con và điền field "Phụ huynh/Người bảo hộ", khi lên đơn hàng chọn Khách hàng = phụ huynh nhưng Học viên (dòng sản phẩm) = con. Mọi theo dõi học tập nằm trên hồ sơ của con.

### 8.7 "Gieo hạt" khác "Thu" (học phí) thế nào?
Cả 2 đều đi qua Đơn hàng/Hóa đơn **giống hệt nhau** — khác ở Sản phẩm dùng (mỗi khóa học có 1 sản phẩm học phí riêng, còn "Gieo hạt" dùng chung 1 sản phẩm cho mọi khoản ủng hộ) và Gieo hạt giá tự nhập mỗi lần thay vì giá niêm yết cố định, không bắt buộc gắn Khóa học/Lớp học.
