# Tình huống vận hành thực tế

Tập hợp các tình huống thực tế có thể xảy ra
Mỗi tình huống có: bối cảnh → hệ thống phản ứng thế nào → người dùng thao tác gì → **hướng dẫn thao tác chi tiết từng bước trên phần mềm**.

---

## Phần 1 — Sale

### Tình huống 1.1: Khách đăng ký khóa "EQ 5 phút" qua website, thanh toán ngay
Chị Lan thấy trang landing "EQ 5 phút", bấm "Đăng ký ngay", điền họ tên/email/sđt (Tab 1) → hệ thống tự tạo **Phiếu đăng ký** trạng thái **Mới đăng ký**, gửi email xác nhận. Chị Lan quét mã QR ở Tab 2 (hiện đang giả lập, chưa phải cổng ngân hàng thật) → ngay khi hệ thống ghi nhận đã thanh toán, **toàn bộ các bước còn lại tự động chạy**: tạo Đơn hàng, xác nhận, xuất Hóa đơn, ghi nhận thanh toán, ghi danh chị Lan vào đúng lớp, Phiếu đăng ký tự chuyển **Hoàn tất** — không cần Sale thao tác gì. Chị Lan trả lời câu hỏi chuyên sâu ở Tab 3 trước hay sau lúc này đều được, không ảnh hưởng tới việc vào lớp.

**Thao tác chi tiết:** không có thao tác bắt buộc — đây là luồng tự động hoàn toàn. Sale chỉ cần:
1. *(Không bắt buộc)* Vào **Đào tạo → Tuyển sinh & Vận hành → Phiếu đăng ký**, mở phiếu của chị Lan để xem lại — phiếu đã ở trạng thái **Hoàn tất**, có sẵn các nút mở nhanh Đơn hàng/Hóa đơn tương ứng.
2. Nếu chị Lan chưa trả lời hết Câu hỏi chuyên sâu, phiếu vẫn hiện trong bộ lọc **"Cần xử lý"** — Sale chủ động nhắn nhắc khách điền nốt, không ảnh hưởng tới việc chị Lan đã vào lớp.

**Biến thể — đăng ký qua điện thoại/Zalo, hoặc hệ thống tự động hóa gặp lỗi:** nếu khách không thanh toán qua website (đăng ký hộ qua điện thoại) hoặc phần tự động gặp lỗi (hiếm gặp), Sale xử lý tay:
1. Vào **Đào tạo → Tuyển sinh & Vận hành → Phiếu đăng ký**, mở phiếu, kiểm tra thông tin cơ bản.
2. Bấm nút **Xác nhận** ở đầu form → trạng thái chuyển "Đã xác nhận".
3. Bấm nút **"Tạo đơn hàng"** vừa xuất hiện → hệ thống tự mở màn hình Báo giá đã điền sẵn Khách hàng/Sản phẩm/Lớp học.
4. Kiểm tra lại dòng sản phẩm trên báo giá, bấm **Xác nhận** để chuyển đơn hàng sang "Đơn bán".
5. Kế toán xuất hóa đơn, ghi nhận thanh toán khi nhận được tiền — hệ thống tự ghi danh học viên + đóng Phiếu đăng ký (xem Tình huống 2.1).

### Tình huống 1.2: Phiếu đăng ký thông tin đáng ngờ (số điện thoại ảo, tên không rõ ràng, trùng lặp thông tin)
Sale mở **Phiếu đăng ký**, thấy số điện thoại không hợp lệ hoặc trùng với 1 phiếu vừa đăng ký 5 phút trước (hệ thống đã tự chặn phần lớn trường hợp trùng lặp trong 15 phút ở bước tạo phiếu, nhưng vẫn có thể lọt) → Sale bấm **Từ chối**, popup bắt buộc nhập lý do (VD "Không liên hệ được, số điện thoại không đúng định dạng") → phiếu chuyển **Đã từ chối**, lý do lưu lại để tra cứu sau nếu khách quay lại đăng ký lần nữa.

**Lưu ý:** cách này chỉ hiệu quả khi phát hiện **trước khi khách thanh toán xong**. Nếu khách đã thanh toán (dù thông tin đáng ngờ), hệ thống đã tự động ghi danh vào lớp ngay lúc đó (xem Tình huống 1.1) — bấm "Từ chối" phiếu lúc này không hủy ngược lại việc ghi danh, cần xử lý riêng ở Đơn hàng/Ghi danh nếu thực sự cần hủy.

**Thao tác chi tiết:**
1. Vào **Đào tạo → Tuyển sinh & Vận hành → Phiếu đăng ký**, mở phiếu nghi vấn.
2. Bấm nút **Từ chối** ở đầu form.
3. Popup hiện ra, nhập lý do vào ô "Lý do từ chối" (bắt buộc, không để trống).
4. Bấm **"Từ chối phiếu"** trong popup để xác nhận → phiếu chuyển "Đã từ chối", lý do được lưu lại trên phiếu.

### Tình huống 1.3: Phụ huynh liên hệ trực tiếp để đăng ký khóa học cho con
Chị Hoa gọi điện muốn đăng ký "Thực hành EQ" cho con gái (Bé An, chưa từng có hồ sơ trong hệ thống). Sale tạo báo giá: với thông tin **Khách hàng** = Chị Hoa (tạo mới ngay tại ô chọn nếu chưa có), trên dòng báo giá/đơn hàng sale thêm dòng sản phẩm khóa học, lớp học, trên ô **Học viên** nhập tên bé An và bấm **Tạo** để tạo thêm hồ sơ liên hệ riêng cho Bé An, hệ thống sẽ tự gắn bé An vào liên hệ liên quan của chị Hoa. Từ lúc này, toàn bộ theo dõi học tập (Ghi danh, điểm danh, chứng chỉ) nằm trên hồ sơ Bé An, hóa đơn vẫn đứng tên Chị Hoa.

**Thao tác chi tiết:**
1. Vào **Bán hàng → Báo giá → Mới**.
2. Ô "Khách hàng": gõ "Chị Hoa" — nếu chưa có hồ sơ, bấm "Tạo" ngay tại ô để tạo nhanh hoặc tạo và chỉnh sửa để cập nhật luôn các thông tin khác của Chị Hoa.
3. Ở dòng sản phẩm: chọn đúng sản phẩm khóa "Thực hành EQ".
4. Ô "Lớp học" trên dòng đó: chọn đúng lớp.
5. Ô "Học viên" trên dòng đó: gõ "Bé An" — chưa có nên bấm "Tạo" → hệ thống tự tạo hồ sơ mới cho Bé An, **tự điền sẵn "Phụ huynh/Người bảo hộ" = Chị Hoa** (do ô Học viên đã cấu hình mặc định vậy, không cần Sale tự chọn tay).
6. Xác nhận đơn hàng.

### Tình huống 1.4: Lớp "EQ 5 phút - K19" sáng đã đầy, khách đăng ký sau bị lỡ
Sale nhận điện thoại của khách muốn đăng ký nhưng lớp sáng K19 đã đủ chỉ tiêu. Sale báo lại Quản lý để đóng đăng ký lớp sáng (chuyển trạng thái "Đã đóng đăng ký") và đổi "Lớp nhận đăng ký" trên Khóa học sang lớp tối K19 (nếu đã mở sẵn) — từ lúc này khách đăng ký mới trên web tự động rơi vào đúng lớp tối, Sale không cần chọn tay từng trường hợp.

**Thao tác chi tiết:**
1. Sale báo Quản lý (Sale không có quyền sửa Lớp học/Khóa học).
2. Quản lý mở form Lớp học "K19 (sáng)", bấm nút **"Đóng đăng ký"**.
3. Quản lý mở form Khóa học "EQ 5 phút", đổi field **"Lớp nhận đăng ký"** sang "K19 (tối)".
4. Lưu lại — Phiếu đăng ký mới tạo từ web từ giờ tự nhận đúng lớp tối, không cần ai chọn tay.

### Tình huống 1.5: Khách hàng cũ gọi hỏi "tôi từng học khóa gì ở Seroto rồi?"
Sale tìm kiếm thông tin theo số điện thoại trong menu **Liên hệ** hoặc menu **Học viên**, mở đúng hồ sơ, thấy ngay 2 field **"Đang học"** và **"Đã học"** hiện sẵn tên các khóa — không cần lật lại từng đơn hàng cũ hay hỏi Kế toán.

**Thao tác chi tiết:**
1. Vào **Liên hệ (Contacts)** hoặc **Đào tạo → Học viên & Nhân Sự → Học viên**.
2. Gõ số điện thoại của khách vào ô tìm kiếm.
3. Mở đúng hồ sơ trả về.
4. Đọc trực tiếp 2 field "Đang học"/"Đã học" ngay trên form (không cần mở tab riêng) để biết khóa đang học và khóa đã hoàn thành.

### Tình huống 1.6: Học viên cũ muốn gửi thêm 1 khoản "gieo hạt" sau khi học xong
Anh Minh nhắn Zalo cho Sale muốn gửi 500.000đ ủng hộ sau khi thấy hiệu quả từ khóa "Trải nghiệm EQ" đã học. Sale lên 1 Đơn hàng cho Anh Minh, thêm dòng sản phẩm **"Gieo hạt"**, sửa giá thành 500.000đ, chọn Lớp học Anh Minh đã học (không bắt buộc, nhưng gắn để sau này lên báo cáo theo khóa) — đúng quy trình như ghi nhận học phí bình thường, không có gì khác lạ.

**Thao tác chi tiết:**
1. Vào **Bán hàng → Đơn hàng → Mới**, chọn Khách hàng = Anh Minh.
2. Thêm dòng sản phẩm, chọn sản phẩm **"Gieo hạt"**.
3. Sửa giá dòng đó thành 500.000.
4. Ô "Lớp học" trên dòng đó — chọn lớp Anh Minh đã học (không bắt buộc, để trống cũng được).
5. Xác nhận đơn hàng → Tạo hóa đơn → Đăng ký thanh toán khi nhận được tiền.

### Tình huống 1.7: Cuối tuần, Sale rà lại các Ghi danh đang "Chờ thanh toán" quá lâu
Sale vào menu **Ghi danh**, bấm bộ lọc **"Chờ thanh toán"**, nhóm theo **Lớp học** để xem lớp nào đang tồn đọng nhiều học viên chưa thanh toán xong, chủ động gọi nhắc khách hoàn tất.

**Thao tác chi tiết:**
1. Vào **Đào tạo → Tuyển sinh & Vận hành → Ghi danh**.
2. Ở ô tìm kiếm, bấm bộ lọc **"Chờ thanh toán"**.
3. Bấm "Nhóm theo" → chọn **"Lớp học"**.
4. Xem danh sách đã nhóm theo từng lớp, ưu tiên gọi nhắc các lớp tồn đọng nhiều nhất.

---

## Phần 2 — Kế toán

### Tình huống 2.1: Xuất hóa đơn học phí, ghi nhận thanh toán
Áp dụng cho đơn hàng **không** đến từ luồng đăng ký online tự động (VD khách đăng ký qua điện thoại — xem biến thể ở Tình huống 1.1). Từ đơn hàng Sale đã xác nhận (khóa "EQ 5 phút", học viên anh Tuấn), Kế toán xuất hóa đơn, sau khi nhận được chuyển khoản thật thì **Ghi nhận thanh toán**. Ngay khi hóa đơn chuyển "Đã thanh toán", hệ thống tự động: ghi danh anh Tuấn vào đúng lớp, tự chuyển Phiếu đăng ký gốc sang **Hoàn tất** (nếu có) — Kế toán không cần quay lại 2 màn hình đó để cập nhật tay.

**Thao tác chi tiết:**
1. Mở đơn hàng đã xác nhận (Bán hàng → Đơn hàng), bấm **"Tạo hóa đơn"**.
2. Trên hóa đơn nháp vừa tạo, bấm **Xác nhận** (Post) để đăng sổ.
3. Bấm nút **"Đăng ký thanh toán"** (Register Payment), kiểm tra đúng số tiền/phương thức thanh toán, bấm xác nhận.
4. Không cần thao tác gì thêm — Ghi danh và Phiếu đăng ký tự cập nhật ngay sau bước 3.

### Tình huống 2.2: Học viên xin hoàn học phí giữa chừng
Học viên hủy giữa khóa, Kế toán lập hóa đơn điều chỉnh giảm (Giấy báo có/Credit Note) cho đúng dòng học phí đó, xác nhận và tất toán. Số tiền này tự động **trừ thẳng** vào cột "Thu (học phí)" trong Báo cáo tổng hợp của đúng khóa đó — Kế toán không cần tính tay phần chênh lệch.

**Thao tác chi tiết:**
1. Mở hóa đơn học phí gốc đã thanh toán (Kế toán → Khách hàng → Hóa đơn).
2. Tìm nút liên quan đến "Giấy báo có"/"Credit Note" ngay trên hóa đơn đó (thường nằm ở đầu form hoặc trong menu Hành động ⚙) — bấm để hệ thống tự tạo 1 hóa đơn điều chỉnh giảm tham chiếu đúng hóa đơn gốc. Nếu không thấy nút này, vào thẳng **Kế toán → Khách hàng → Giấy báo có → Mới**, tự chọn khách hàng + dòng sản phẩm học phí cần hoàn tương ứng.
3. Xác nhận (Đăng sổ) hóa đơn điều chỉnh vừa tạo.
4. Bấm **"Đăng ký thanh toán"**/tất toán cho khoản hoàn tiền này — chỉ khi trạng thái thanh toán về "Đã thanh toán" thì số tiền mới tự trừ vào Báo cáo tổng hợp.

### Tình huống 2.3: Trả tiền thuê hội trường cho lớp "Thực hành EQ - K19"
Kế toán nhận hóa đơn từ đơn vị cho thuê hội trường 3.000.000đ. Vào **Kế toán → Nhà cung cấp → Hóa đơn → Mới**, chọn nhà cung cấp, thêm dòng chi phí, ở cột **"Lớp học"** ngay trên dòng đó chọn đúng lớp K19 (không cần thiết lập gì trước, chọn trực tiếp) → xác nhận hóa đơn. Khoản chi này tự động cộng vào cột "Chi" của đúng lớp K19 trong Báo cáo tổng hợp.

**Thao tác chi tiết:**
1. Vào **Kế toán → Nhà cung cấp → Hóa đơn → Mới**.
2. Chọn Nhà cung cấp.
3. Thêm dòng chi phí: mô tả, số tiền 3.000.000.
4. Trên chính dòng đó, cột **"Lớp học"** — chọn lớp K19.
5. Bấm Xác nhận (Đăng sổ) hóa đơn.
6. Bấm "Đăng ký thanh toán" khi đã thực chi.

### Tình huống 2.4: Chi phí văn phòng, không liên quan khóa học nào
Hóa đơn tiền điện văn phòng — Kế toán ghi nhận bình thường nhưng **để trống cột "Lớp học"**. Khoản này vẫn vào sổ kế toán chung của công ty, chỉ là không xuất hiện trong Báo cáo tổng hợp theo khóa học (đúng chủ đích, tránh lẫn chi phí vận hành chung vào chi phí đào tạo).

**Thao tác chi tiết:**
1. Làm giống các bước 1-3, 5-6 của Tình huống 2.3.
2. Ở bước chọn cột "Lớp học" — **không chọn gì, để trống**.

### Tình huống 2.5: Một tổ chức bên ngoài muốn tài trợ cho Seroto, không liên quan khóa học nào
Một công ty liên hệ muốn ủng hộ 10.000.000đ cho hoạt động của Seroto nói chung. Kế toán/Sale lên Đơn hàng, tạo hồ sơ liên hệ cho công ty đó (tick "Là công ty" trên Liên hệ), thêm dòng sản phẩm **"Gieo hạt"** với giá 10.000.000đ, **để trống Lớp học** vì đây là ủng hộ chung.

**Thao tác chi tiết:**
1. Vào **Bán hàng → Đơn hàng → Mới**.
2. Ô "Khách hàng": gõ tên công ty, bấm "Tạo và Sửa" để mở form liên hệ mới, tick **"Là công ty"**, lưu lại.
3. Thêm dòng sản phẩm, chọn sản phẩm **"Gieo hạt"**, sửa giá thành 10.000.000.
4. Để trống ô "Lớp học" trên dòng đó.
5. Xác nhận đơn hàng → Tạo hóa đơn → Đăng ký thanh toán khi nhận được tiền.

### Tình huống 2.6: Cuối tháng, đối chiếu Thu — Chi theo từng khóa để báo cáo lên Quản lý
Kế toán mở **Báo cáo tổng hợp**, dùng Pivot xem theo Tháng, lọc riêng loại số liệu "Thu (học phí)" và "Chi" theo từng Khóa học/Lớp học — biết ngay khóa nào đang lãi, khóa nào đang lỗ trong tháng, không cần cộng tay từ nhiều hóa đơn.

**Thao tác chi tiết:**
1. Vào **Đào tạo → Báo cáo & Cấu hình → Báo cáo tổng hợp** (mặc định mở Pivot).
2. Ở ô tìm kiếm, tick 2 bộ lọc **"Thu (học phí)"** và **"Chi"** (bỏ chọn các loại số liệu khác nếu muốn nhìn gọn hơn).
3. Cột đã mặc định theo Tháng — bấm mở rộng để xem từng tháng cụ thể.
4. Bấm mở rộng hàng Khóa học để xem xuống từng Lớp học nếu cần chi tiết hơn.

---

## Phần 3 — Quản lý (Khóa học, việc học tập, dữ liệu Đào tạo)

### Tình huống 3.1: Mở 1 khóa học hoàn toàn mới
Seroto muốn ra mắt khóa "Trải nghiệm EQ". Quản lý vào **Đào tạo → Khóa học → Mới**, điền tên/mô tả/hình thức học, **bắt buộc gắn Sản phẩm liên kết** (nếu chưa có, tạo sản phẩm dịch vụ mới bên Bán hàng trước), cấu hình sẵn bộ **Câu hỏi chuyên sâu** riêng cho khóa này để dùng ở Tab Câu hỏi chuyên sâu form đăng ký web.

**Thao tác chi tiết:**
1. (Nếu chưa có sản phẩm) Vào **Bán hàng → Sản phẩm → Mới**, tạo sản phẩm loại "Dịch vụ", đặt tên/giá bán học phí.
2. Vào **Đào tạo → Khóa học → Mới**.
3. Điền Tên khóa học, Mã khóa học, Slogan, Mô tả chi tiết, Hình thức học.
4. Ô "Sản phẩm liên kết" — chọn đúng sản phẩm vừa tạo ở bước 1.
5. Tab "Câu hỏi chuyên sâu" — bấm thêm dòng, nhập nội dung câu hỏi + chọn kiểu (văn bản tự do/trắc nghiệm).
6. Nhập vào tab **Khu vực hiển thị trên website** để xác định vị trí sẽ hiển thị trên website (lưu ý mã cần khớp với mã đã thiết lập cho khối ở trên website)
7. Lưu khóa học.
8. Sau khi lưu thì có thể **Mở đợt học mới**

### Tình huống 3.2: Mở đợt tuyển sinh mới (K19) cho khóa đã có sẵn
Khóa "EQ 5 phút" đã chạy được vài đợt, giờ mở tiếp K19. Quản lý mở form Khóa học, bấm **"Mở đợt học mới"**: nhập mã đợt "K19", ngày dự kiến, chọn giáo viên, tick "Đặt làm lớp nhận đăng ký" → hệ thống tự tạo Đợt học + Lớp học (trạng thái **Sắp mở**). Quản lý bấm tiếp nút **"Mở đăng ký"** trên form Lớp học khi sẵn sàng công bố tuyển sinh. Về sau, khi phát sinh chi phí cho lớp này, Kế toán chỉ cần chọn thẳng lớp K19 ở cột "Lớp học" ngay trên dòng hóa đơn nhà cung cấp (xem Tình huống 2.3), không cần thiết lập gì thêm ở đây.

**Thao tác chi tiết:**
1. Mở form Khóa học "EQ 5 phút".
2. Bấm nút **"Mở đợt học mới"** ở đầu form.
3. Điền Mã đợt "K19", Ngày bắt đầu/kết thúc dự kiến, chọn Giáo viên.
4. Tick "Đặt làm lớp nhận đăng ký" nếu muốn khách đăng ký web tự rơi vào lớp này.
5. Bấm **"Mở đợt học"** để xác nhận wizard.
6. Mở tab "Đợt học & Lớp học" trên form Khóa học, mở đúng lớp K19 vừa tạo.
7. Khi sẵn sàng công bố tuyển sinh, bấm nút **"Mở đăng ký"** trên form Lớp học.

### Tình huống 3.3: Lớp K19 sáng đăng ký đông hơn dự kiến, cần mở thêm lớp tối
Quản lý vào menu Lớp học, tạo lớp mới, chọn **cùng Đợt học K19** đã có (không tạo Đợt học mới), đặt tên "EQ 5 phút - K19 (tối)", gán giáo viên khác nếu cần — 2 lớp cùng đợt chạy song song bình thường, không giới hạn.

**Thao tác chi tiết:**
1. Vào **Đào tạo → Khóa học → Lớp học → Mới**.
2. Ô "Đợt học" — chọn đúng "K19" đã có sẵn (không tạo Đợt học mới ở đây).
3. Đặt tên lớp "EQ 5 phút - K19 (tối)".
4. Gán Giáo viên phù hợp.
5. Lưu, bấm nút **"Mở đăng ký"** khi sẵn sàng nhận học viên.

### Tình huống 3.4: Gán nhân sự vận hành cho 1 lớp
Trên form Lớp học K19: gán **Giảng viên** (người đứng lớp, phải đã tick "Là giảng viên"), **Ban tổ chức** (nhân sự chính thức hỗ trợ vận hành), và **Người phụng sự** (1-2 bạn tình nguyện hỗ trợ việc nhỏ, KHÔNG phải Ban tổ chức chính thức, KHÔNG được xem dữ liệu học viên). 3 nhóm này tách biệt hoàn toàn trên cùng 1 form.

**Thao tác chi tiết:**
1. Mở form Lớp học K19.
2. Ô "Giảng viên" — chọn người đã tick "Là giảng viên" trên hồ sơ liên hệ (nếu chưa tick, vào hồ sơ liên hệ đó tick trước).
3. Ô "Ban tổ chức" — chọn thành viên chính thức phụ trách.
4. Ô "Người phụng sự" — chọn tình nguyện viên hỗ trợ, không chọn lẫn vào 2 ô trên.
5. Lưu form.

### Tình huống 3.5: Theo dõi buổi học Zoom xen kẽ buổi thực hành (BTH)
Lịch học K19 có cả buổi học lý thuyết qua Zoom và buổi thực hành trực tiếp (BTH). Quản lý/giáo viên tạo từng buổi học, chọn đúng phân loại (`Zoom` hoặc `BTH`) khi tạo. Cuối đợt, xem form Ghi danh của từng học viên sẽ thấy tách riêng "Điểm danh Zoom: 5/6" và "Điểm danh BTH: 3/4" — biết chính xác học viên vắng nhiều ở loại buổi học nào để nhắc nhở.

**Thao tác chi tiết:**
1. Mở form Lớp học K19, tab "Danh sách Buổi học".
2. Bấm thêm dòng, nhập Tên buổi học, Thời gian bắt đầu/kết thúc.
3. Chọn **"Phân loại buổi học"** = Zoom hoặc BTH (mặc định Zoom nếu không đổi).
4. Lưu buổi học, mở lại buổi học đó, bấm **"Khởi tạo danh sách điểm danh"**.
5. Đánh dấu Có mặt/Đi muộn/Vắng cho từng học viên trong buổi.
6. Cuối đợt: vào **Đào tạo → Tuyển sinh & Vận hành → Ghi danh**, mở từng học viên, xem 2 field "Điểm danh Zoom"/"Điểm danh BTH" để biết học viên vắng nhiều ở loại buổi nào.

### Tình huống 3.6: Cuối đợt K19, đánh giá tổng thể để quyết định mở tiếp K20
Quản lý mở **Báo cáo tổng hợp**, lọc theo Khóa học "EQ 5 phút" và Lớp học "K19", xem đủ trong 1 màn hình: bao nhiêu học viên tham gia, bao nhiêu hoàn thành, bao nhiêu người phụng sự đã hỗ trợ, tổng tiền gieo hạt nhận được, và Thu trừ Chi có dương không — làm căn cứ quyết định có mở tiếp K20 hay điều chỉnh gì trước khi mở.

**Thao tác chi tiết:**
1. Vào **Đào tạo → Báo cáo & Cấu hình → Báo cáo tổng hợp**.
2. Ở ô tìm kiếm, gõ/chọn Khóa học "EQ 5 phút".
3. Bấm mở rộng hàng Khóa học để xem xuống đúng dòng Lớp học "K19".
4. Đọc lần lượt các cột: Học viên tham gia, Hoàn thành, Người phụng sự, Gieo hạt, Thu, Chi — so sánh Thu và Chi để biết đợt này lãi hay lỗ.

### Tình huống 3.7: Đóng lớp sau khi kết thúc khóa học
Sau buổi học cuối, Quản lý vào form Lớp học K19, bấm lần lượt **"Đóng đăng ký"** (nếu chưa đóng từ trước) → **"Bắt đầu học"** (nếu quên chuyển lúc khai giảng) → **"Hoàn thành"**. Các học viên có Ghi danh "Đã ghi danh" vẫn cần được xử lý riêng (bấm "Hoàn thành & Cấp chứng chỉ" ở từng Ghi danh) — trạng thái Lớp học và trạng thái Ghi danh của từng học viên là 2 việc tách biệt, không tự động theo nhau.

**Thao tác chi tiết:**
1. Mở form Lớp học K19.
2. Bấm **"Đóng đăng ký"** (nếu lớp còn đang mở nhận học viên).
3. Bấm **"Bắt đầu học"** (nếu chưa chuyển từ lúc khai giảng).
4. Sau buổi học cuối, bấm **"Hoàn thành"**.
5. Vào **Đào tạo → Tuyển sinh & Vận hành → Ghi danh**, lọc theo Lớp học "K19" và trạng thái "Đã ghi danh".
6. Mở từng bản ghi, bấm **"Hoàn thành & Cấp chứng chỉ"** cho từng học viên đủ điều kiện — bước này không tự động chạy theo bước 4. Chứng chỉ chỉ được cấp qua đúng nút này (không tạo tay được ở màn hình danh sách Chứng chỉ), và mỗi Ghi danh chỉ được cấp tối đa 1 Chứng chỉ dù bấm nhiều lần.

### Tình huống 3.8: Cho khóa "EQ 5 phút" xuất hiện ở trang dành riêng cho Giáo viên
Quản lý muốn khóa "EQ 5 phút" hiển thị ở khu vực trang web dành cho Giáo viên. Vào form Khóa học "EQ 5 phút", tab **"Khu vực hiển thị"**, thêm dòng chọn (hoặc tạo mới nếu chưa có) khu vực "Giáo viên" — khóa học tự xuất hiện ở đúng khu vực đó trên website, không cần thao tác gì thêm bên ngoài.

**Thao tác chi tiết:**
1. Mở form Khóa học "EQ 5 phút".
2. Vào tab **"Khu vực hiển thị"**.
3. Bấm thêm dòng, chọn khu vực "Giáo viên" (nếu chưa có, gõ tên mới và tạo luôn tại chỗ, kèm 1 Mã khu vực riêng để cấu hình bên website).
4. Lưu khóa học — website tự cập nhật theo.

Quản lý danh sách đầy đủ các khu vực đang có tại **Đào tạo → Báo cáo & Cấu hình → Khu vực hiển thị trên website**.

---

## Ghi chú phạm vi

- Tất cả tình huống trên đều dựa trên tính năng **đã triển khai thật** trong phần mềm — không có tình huống giả định cho phần còn thiếu (VD chưa xử lý được luồng CRM Zalo/Facebook, chưa tách "Thu" theo lớp 100% trường hợp, chưa có nơi theo dõi "chi phí chung").
- Cổng thanh toán trong Tình huống 1.1 vẫn đang **giả lập**, chưa nối ngân hàng thật.
