# viettotal_seroto_edu

**Module quản lý trung tâm giáo dục trên Odoo 19 Community**
Phát triển bởi [Viettotal](https://viettotal.com) · Phiên bản `19.0.1.0.0`

---

## Mục lục

1. [Tổng quan](#1-tổng-quan)
2. [Luồng dữ liệu chính](#2-luồng-dữ-liệu-chính)
3. [Yêu cầu hệ thống](#3-yêu-cầu-hệ-thống)
4. [Cài đặt](#4-cài-đặt)
5. [Cấu trúc thư mục](#5-cấu-trúc-thư-mục)
6. [Models](#6-models)
7. [Website & Form đăng ký](#7-website--form-đăng-ký)
8. [Backend Views & Menu](#8-backend-views--menu)
9. [Phân quyền](#9-phân-quyền)
10. [Sequences (Mã tự động)](#10-sequences-mã-tự-động)
11. [Hướng dẫn sử dụng](#11-hướng-dẫn-sử-dụng)
12. [Tuỳ chỉnh & Mở rộng](#12-tuỳ-chỉnh--mở-rộng)

---

## 1. Tổng quan

`viettotal_seroto_edu` là module Odoo 19 Community quản lý **toàn bộ vòng đời học viên** tại một trung tâm giáo dục ngoại ngữ / kỹ năng:

- **Website công khai**: Landing page khoá học + Form đăng ký 4 bước + Tra cứu hồ sơ
- **Tuyển sinh**: Tiếp nhận lead từ website/CRM → Tư vấn → Ký hợp đồng → Thanh toán → Nhập học
- **Quản lý học tập**: Lớp học, buổi học, điểm danh, bài tập, tài liệu, tiến độ
- **Kiểm tra & Đánh giá**: Thi, chấm điểm, xếp loại theo nhiều thang (IELTS/TOEIC/thang 10)
- **Chứng chỉ**: Cấp phát, mã xác minh QR, in theo mẫu
- **Chăm sóc học viên (CRM Care)**: Log tương tác, NPS/khảo sát, kế hoạch follow-up, upsell

---

## 2. Luồng dữ liệu chính

```
WEBSITE (Form đăng ký)
        │
        ▼
   crm.lead  ←── UTM Source/Medium/Campaign
        │
        ▼
 res.partner (Contact)
        │
        ▼
 edu.admission (Hồ sơ tuyển sinh)
   [new → consulting → registered → contracted → paid → enrolled]
        │
        ▼
  edu.student (Học viên)
        │
        ├──► edu.enrollment (Đăng ký học) ──► edu.course.class (Lớp học)
        │                                              │
        │                                    edu.session (Buổi học)
        │                                              │
        │                                    edu.attendance (Điểm danh)
        │
        ├──► edu.exam → edu.exam.result (Kết quả kiểm tra)
        │
        ├──► edu.certificate (Chứng chỉ)
        │
        └──► edu.care.activity / edu.care.schedule (Chăm sóc)
                        │
                        └──► crm.lead mới (Upsell khoá tiếp theo)
```

---

## 3. Yêu cầu hệ thống

| Thành phần | Yêu cầu |
|-----------|---------|
| Odoo | **19.0 Community** |
| Python | 3.10+ |
| Module phụ thuộc | `base`, `mail`, `crm`, `sale_management`, `utm`, `hr`, `website`, `website_crm` |

> **Lưu ý:** Module `website` và `website_crm` cần được cài trước. Nếu không dùng website, có thể bỏ 2 dependency này và xoá thư mục `controllers/` + `views/website/`.

---

## 4. Cài đặt

### Bước 1 – Sao chép module vào addons path

```bash
cp -r viettotal_seroto_edu/ /path/to/odoo/addons/
# hoặc thêm đường dẫn vào odoo.conf:
# addons_path = /path/to/custom_addons
```

### Bước 2 – Cập nhật danh sách module

```bash
# Qua giao diện
Settings → Activate developer mode → Apps → Update Apps List

# Hoặc qua CLI
./odoo-bin -u viettotal_seroto_edu -d <tên_database>
```

### Bước 3 – Cài đặt module

Vào **Apps** → tìm `Seroto Education` → **Install**

### Bước 4 – Cấu hình ban đầu

Sau khi cài, vào **Seroto Edu → Cấu hình** để thiết lập:

| Mục | Nơi cấu hình |
|-----|-------------|
| Danh mục khoá học | Cấu hình → Danh mục khoá học |
| Phòng học / Cơ sở | Cấu hình → Phòng học |
| Loại kiểm tra | Cấu hình → Loại kiểm tra |
| Mẫu chứng chỉ | Cấu hình → Mẫu chứng chỉ |
| Danh mục chăm sóc | Cấu hình → Danh mục chăm sóc |
| Tags học viên | Cấu hình → Tags học viên |

---

## 5. Cấu trúc thư mục

```
viettotal_seroto_edu/
│
├── __init__.py
├── __manifest__.py
│
├── controllers/
│   ├── __init__.py
│   └── website_registration.py      # Routes website công khai
│
├── data/
│   └── ir_sequence_data.xml         # Sequences mã tự động
│
├── models/
│   ├── __init__.py
│   ├── edu_academic.py              # Khoá học, Lớp học, Buổi học, Phòng học
│   ├── edu_admission.py             # Hồ sơ tuyển sinh
│   ├── edu_assessment.py            # Kiểm tra, Kết quả thi
│   ├── edu_attendance.py            # Điểm danh + Wizard
│   ├── edu_care.py                  # Chăm sóc học viên (CRM Care)
│   ├── edu_certificate.py           # Chứng chỉ
│   ├── edu_learning.py              # Giáo trình, Tài liệu, Bài tập, Tiến độ
│   ├── edu_parent.py                # Phụ huynh / Người bảo lãnh
│   ├── edu_student.py               # Học viên + Đăng ký học
│   └── edu_teacher.py               # Giáo viên
│
├── security/
│   └── ir.model.access.csv          # Phân quyền truy cập
│
├── static/
│   └── src/
│       ├── css/
│       │   └── website_registration.css   # CSS landing page + form
│       └── js/
│           └── website_registration.js    # Multi-step form + AJAX
│
└── views/
    ├── view_academic.xml            # Views khoá học, lớp, buổi, phòng
    ├── view_admission.xml           # Views tuyển sinh
    ├── view_assessment.xml          # Views kiểm tra
    ├── view_attendance.xml          # Views điểm danh + tiến độ
    ├── view_care.xml                # Views chăm sóc
    ├── view_certificate.xml         # Views chứng chỉ
    ├── view_learning.xml            # Views học tập
    ├── view_menu.xml                # Menu chính
    ├── view_student.xml             # Views học viên
    ├── view_teacher.xml             # Views giáo viên
    └── website/
        ├── assets.xml               # Asset bundle + menu navbar
        ├── website_form.xml         # QWeb: Form đăng ký 4 bước
        ├── website_landing.xml      # QWeb: Landing page khoá học
        └── website_thankyou_lookup.xml  # QWeb: Cảm ơn + Tra cứu
```

**Tổng cộng: ~6.700 dòng code** (10 models + 10 views backend + 4 views website + 1 controller + CSS/JS)

---

## 6. Models

### 6.1 `edu.admission` – Hồ sơ tuyển sinh

Quản lý toàn bộ quá trình từ khi tiếp nhận lead đến khi học viên nhập học.

**Trạng thái (state):**

```
new → consulting → registered → contracted → paid → enrolled
                                                  └→ cancelled
```

**Trường quan trọng:**

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `name` | Char | Mã hồ sơ (tự động: `ADM/2024/00001`) |
| `student_name` | Char | Họ tên học viên |
| `phone` / `email` | Char | Liên lạc |
| `crm_lead_id` | Many2one | Lead CRM gốc |
| `partner_id` | Many2one | Contact Odoo |
| `sale_order_id` | Many2one | Đơn hàng |
| `course_id` / `course_class_id` | Many2one | Khoá / Lớp đăng ký |
| `admission_channel` | Selection | Website/Facebook/Zalo/Giới thiệu… |
| `tuition_fee` / `final_fee` | Monetary | Học phí / Thực thu |
| `payment_status` | Selection | unpaid/partial/paid |
| `student_id` | Many2one | Học viên được tạo sau nhập học |

**Action đặc biệt:**
- `action_enroll()` → Tự động tạo `edu.student` từ hồ sơ và chuyển sang `enrolled`

---

### 6.2 `edu.student` – Học viên

Thực thể trung tâm của hệ thống.

**Trạng thái:** `active` → `on_leave` / `graduated` / `dropped_out` / `suspended`

**Trường quan trọng:**

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `student_code` | Char | Mã học viên (tự động: `HV/00001`) |
| `english_level` | Selection | Trình độ đầu vào (6 cấp) |
| `target_cert` / `target_score` | Char/Float | Chứng chỉ và điểm mục tiêu |
| `enrollment_ids` | One2many | Danh sách đăng ký học |
| `parent_ids` | One2many | Phụ huynh / người bảo lãnh |
| `care_staff_id` | Many2one | Nhân viên chăm sóc phụ trách |
| `tag_ids` | Many2many | Tags phân loại |

**Model liên quan:**
- `edu.enrollment` – Bảng trung gian học viên ↔ lớp học (có state riêng, học phí)
- `edu.student.tag` – Tags màu sắc

---

### 6.3 `edu.teacher` – Giáo viên

| Trường | Mô tả |
|--------|-------|
| `teacher_code` | Mã GV (tự động: `GV/0001`) |
| `specialization` | Chuyên môn / môn dạy |
| `degree` | Bằng cấp (college → phd → native) |
| `certificate_ids` | Danh sách chứng chỉ GV (IELTS, TOEIC…) |
| `salary_type` | Lương cố định / theo buổi / theo học viên |
| `user_id` / `employee_id` | Liên kết tài khoản và hồ sơ HR |

---

### 6.4 `edu.parent` – Phụ huynh / Người bảo lãnh

Gắn với học viên qua `student_id`. Hỗ trợ đánh dấu `is_payer` (người thanh toán) và `is_primary_contact` (đầu mối liên lạc chính).

---

### 6.5 `edu.course` / `edu.course.class` / `edu.session` – Học thuật

**Hierarchy:**

```
edu.course (Khoá học)
    └── edu.course.class (Lớp học)  ← gắn giáo viên, phòng, lịch
            └── edu.session (Buổi học)  ← gắn điểm danh
```

**`edu.course.class` tính tự động:**
- `enrolled_count` – Số học viên đã đăng ký
- `available_seats` – Chỗ trống còn lại (`max_students - enrolled_count`)
- `session_count` – Số buổi học

**`edu.room`** – Phòng học / địa điểm (classroom / lab / online)

---

### 6.6 `edu.learning` – Nội dung học tập

| Model | Mô tả |
|-------|-------|
| `edu.syllabus` | Giáo trình theo chương/bài |
| `edu.syllabus.unit` | Bài học đơn vị |
| `edu.material` | Tài liệu (PDF, video, link, bài tập) |
| `edu.assignment` | Bài tập về nhà / dự án / thuyết trình |
| `edu.assignment.submission` | Bài nộp của từng học viên |
| `edu.learning.progress` | Tiến độ học tập: chuyên cần, điểm TB, cờ chú ý |

**Cờ `needs_attention`** trên `edu.learning.progress`: Giáo viên đánh dấu → nhân viên chăm sóc nhận alert để follow-up.

---

### 6.7 `edu.attendance` – Điểm danh

**Trạng thái điểm danh:** `present` / `absent` / `absent_leave` / `late` / `early_leave` / `online`

`is_counted_present` (computed): `present`, `late`, `online`, `early_leave` đều tính là có mặt.

**Sau mỗi lần điểm danh**, hệ thống tự cập nhật `edu.learning.progress.sessions_attended`.

**Wizard `edu.attendance.wizard`**: Điểm danh hàng loạt cho toàn bộ học viên một buổi trong một thao tác.

---

### 6.8 `edu.exam` / `edu.exam.result` – Kiểm tra & Đánh giá

**Phương thức chấm điểm (`scoring_method`):**

| Loại | Thang | Xếp loại tự động |
|------|-------|-----------------|
| `points` | 0–10 | Xuất sắc/Giỏi/Khá/TB/Yếu |
| `band` | 0–9 (IELTS) | Xuất sắc/Giỏi/Khá/TB/Chưa đạt |
| `toeic` | 10–990 | C/B2/B1/A2/A1 |
| `percent` | 0–100% | Tương tự points |
| `pass_fail` | Đạt/Không | — |

`action_generate_results()` → Tự tạo `edu.exam.result` cho toàn bộ học viên trong lớp.

---

### 6.9 `edu.certificate` – Chứng chỉ

| Trường | Mô tả |
|--------|-------|
| `name` | Số chứng chỉ (tự động: `CERT/2024/00001`) |
| `template_id` | Mẫu chứng chỉ (nội bộ / IELTS / TOEIC / Cambridge…) |
| `verification_code` | Mã xác minh 12 ký tự (UUID) |
| `date_issued` / `date_expiry` | Ngày cấp / hết hạn (tự tính từ `validity_months`) |
| `certificate_file` | File PDF đính kèm |

`action_issue()` → Cấp chứng chỉ, tính ngày hết hạn tự động.

---

### 6.10 `edu.care` – Chăm sóc học viên

| Model | Mô tả |
|-------|-------|
| `edu.care.activity` | Log từng lần tương tác: gọi điện, SMS, Zalo, gặp trực tiếp… |
| `edu.care.feedback` | Khảo sát NPS + đánh giá chi tiết (GV, nội dung, cơ sở…) |
| `edu.care.schedule` | Kế hoạch chăm sóc định kỳ (welcome / giữa khoá / pre-exam…) |

**Phân loại NPS tự động:**

```
9–10  → Promoter   (Người ủng hộ)
7–8   → Passive    (Thụ động)
0–6   → Detractor  (Người phàn nàn – cần xử lý ưu tiên)
```

**`result` của care.activity:**

- `at_risk` → Ribbon đỏ "Nguy cơ nghỉ học" → cần xử lý ngay
- `upsell_done` → Ribbon xanh → tạo `crm.lead` mới cho khoá tiếp theo

---

## 7. Website & Form đăng ký

### 7.1 Routes công khai

| Route | Method | Chức năng |
|-------|--------|-----------|
| `/dang-ky` | GET | Landing page – danh sách khoá học đang mở |
| `/dang-ky/form` | GET | Form đăng ký 4 bước (hỗ trợ `?course_id=X`) |
| `/dang-ky/form/submit` | POST | Xử lý đăng ký → tạo Lead + Hồ sơ |
| `/dang-ky/get-classes` | JSON/POST | AJAX: lấy danh sách lớp theo khoá |
| `/dang-ky/cam-on` | GET | Trang cảm ơn + hiển thị mã hồ sơ |
| `/dang-ky/tra-cuu` | GET/POST | Tra cứu tình trạng hồ sơ theo SĐT/email |

### 7.2 Form đăng ký 4 bước

Dữ liệu thu thập theo đúng tài liệu khai thác học viên:

```
Bước 1 – Khoá học & Nguồn
  ├── Chọn khoá học (dropdown)
  ├── Chọn lịch học (load AJAX khi đổi khoá, hiển thị dạng card)
  ├── Kênh biết đến (Website/Facebook/Zalo/Giới thiệu/Telesales/Walk-in)
  └── Tên người giới thiệu

Bước 2 – Thông tin cá nhân
  ├── Họ và tên * / Ngày sinh / Giới tính
  ├── SĐT * / Email
  ├── CMND/CCCD
  ├── Trình độ học vấn / Nghề nghiệp / Nơi làm việc
  └── Địa chỉ thường trú / hiện tại

Bước 3 – Trình độ & Mục tiêu
  ├── Trình độ tiếng Anh hiện tại (6 cấp, dạng card chọn)
  ├── Chứng chỉ mục tiêu (IELTS/TOEIC…) + Điểm mục tiêu
  ├── Mục tiêu học tập chi tiết (textarea)
  └── Thời gian có thể học

Bước 4 – Phụ huynh & Xác nhận
  ├── Toggle: Cung cấp thông tin phụ huynh (optional)
  │     ├── Họ tên phụ huynh / SĐT / Quan hệ
  ├── Ghi chú / yêu cầu đặc biệt
  └── Checkbox đồng ý điều khoản * + Nút Submit
```

### 7.3 Luồng xử lý khi submit

```python
POST /dang-ky/form/submit
  │
  ├─ Validate: student_name, phone, course_id bắt buộc
  │
  ├─ Tìm / tạo res.partner (theo SĐT)
  │
  ├─ Tạo crm.lead
  │     name = "[Đăng ký web] {tên} – {khoá}"
  │     source = UTM "website"
  │
  ├─ Tạo edu.admission
  │     gắn crm_lead_id, partner_id
  │     state = 'new'
  │     tuition_fee = lấy từ edu.course
  │
  └─ Redirect → /dang-ky/cam-on?ref=ADM/2024/xxxxx
```

### 7.4 UI/UX

- **Multi-step**: Progress bar 4 bước, validate từng bước trước khi Next
- **AJAX class loader**: Chọn khoá → tự động load danh sách lớp + ghế còn trống
- **Sticky CTA**: Nút "Đăng ký học" + "Tra cứu hồ sơ" nổi góc phải màn hình
- **Navbar**: Menu "✏️ Đăng ký học" tự gắn vào header website Odoo
- **Palette màu**: Navy `#1A2B4A` · Amber `#F5A623` · White/Gray

---

## 8. Backend Views & Menu

### 8.1 Cấu trúc menu chính

```
Seroto Edu (icon app)
├── Tuyển sinh
│   ├── Hồ sơ tuyển sinh       (list/kanban/form)
│   └── Đăng ký học             (list/form)
│
├── Học viên
│   ├── Danh sách học viên      (list/kanban/form)
│   └── Tiến độ học tập         (list/form)
│
├── Khoá học
│   ├── Khoá học                (kanban/list/form)
│   ├── Lớp học                 (list/form)
│   ├── Buổi học                (list/form)
│   └── Giáo viên               (kanban/list/form)
│
├── Học tập
│   ├── Điểm danh               (list/form)
│   ├── Điểm danh buổi học      (wizard)
│   ├── Bài tập                 (list/form)
│   ├── Tài liệu học tập        (list/form)
│   └── Giáo trình              (list/form)
│
├── Kiểm tra
│   ├── Bài kiểm tra            (list/form)
│   ├── Kết quả thi             (list)
│   └── Chứng chỉ               (list/form)
│
├── Chăm sóc
│   ├── Kế hoạch chăm sóc       (list/form)
│   ├── Log tương tác           (list/kanban/form)
│   └── Phản hồi & Khảo sát     (list/form)
│
└── Cấu hình
    ├── Danh mục khoá học
    ├── Phòng học
    ├── Loại kiểm tra
    ├── Mẫu chứng chỉ
    ├── Danh mục chăm sóc
    └── Tags học viên
```

### 8.2 Đặc điểm views nổi bật

- **Hồ sơ tuyển sinh**: Kanban group by `state`, nút workflow có confirm dialog
- **Học viên**: Tab phụ huynh, đăng ký học, bảo lưu; stat button đếm enrollment
- **Lớp học**: Stat button học viên + buổi học; list học viên inline editable
- **Tiến độ học tập**: Widget `progressbar` chuyên cần; decoration đỏ khi `needs_attention`
- **Bài kiểm tra**: 3 stat buttons (tổng/đạt/không đạt); nhập điểm inline trực tiếp
- **Chứng chỉ**: Ribbon trạng thái; nút in; field mã xác minh
- **Log chăm sóc**: Kanban group by `result`; ribbon "Nguy cơ nghỉ học" / "Upsell thành công"
- **Phản hồi NPS**: Widget `priority` 10 sao; badge tự động Promoter/Passive/Detractor

---

## 9. Phân quyền

Mặc định có 2 cấp quyền cho mỗi model:

| Nhóm | Quyền |
|------|-------|
| `base.group_user` (Người dùng thường) | Read, Write, Create (không xoá) |
| `base.group_system` (Admin) | Read, Write, Create, Unlink (đầy đủ) |

> Để tạo nhóm quyền riêng (VD: `Tư vấn viên`, `Giáo viên`, `Chăm sóc`), thêm vào `security/groups.xml` và cập nhật `ir.model.access.csv`.

---

## 10. Sequences (Mã tự động)

| Model | Format | Ví dụ |
|-------|--------|-------|
| `edu.admission` | `ADM/{year}/{5 số}` | `ADM/2024/00001` |
| `edu.student` | `HV/{5 số}` | `HV/00001` |
| `edu.teacher` | `GV/{4 số}` | `GV/0001` |
| `edu.enrollment` | `ENR/{year}/{5 số}` | `ENR/2024/00001` |
| `edu.certificate` | `CERT/{year}/{5 số}` | `CERT/2024/00001` |
| `edu.care.feedback` | `FB/{year}/{4 số}` | `FB/2024/0001` |

---

## 11. Hướng dẫn sử dụng

### Quy trình tuyển sinh đầy đủ

```
1. Học viên điền form trên /dang-ky/form
        ↓
2. Hệ thống tự tạo crm.lead + edu.admission (state: new)
        ↓
3. Tư vấn viên nhận thông báo → vào Tuyển sinh → Hồ sơ tuyển sinh
   → Gọi điện tư vấn → Click "Xác nhận đăng ký" (state: registered)
        ↓
4. Ký hợp đồng → Click "Ký hợp đồng" (state: contracted)
        ↓
5. Thu tiền → Click "Xác nhận thanh toán" (state: paid)
        ↓
6. Click "Nhập học → Tạo học viên" → Tự tạo edu.student (state: enrolled)
        ↓
7. Thêm học viên vào lớp học qua tab "Đăng ký học" của học viên
```

### Điểm danh buổi học

```
1. Vào Học tập → Điểm danh buổi học (Wizard)
2. Chọn buổi học cần điểm danh
3. Hệ thống tự load danh sách học viên của lớp
4. Chọn trạng thái từng học viên: Có mặt / Vắng / Đi trễ…
5. Click "Xác nhận điểm danh"
   → Tạo edu.attendance cho từng học viên
   → Cập nhật edu.learning.progress tự động
   → Buổi học chuyển sang state "Đã học"
```

### Cấp chứng chỉ

```
1. Vào Kiểm tra → Chứng chỉ → Tạo mới
2. Chọn học viên, lớp học, mẫu chứng chỉ
3. Điền điểm và xếp loại (hoặc liên kết kết quả thi)
4. Click "Cấp chứng chỉ" → Tự điền ngày cấp, tính ngày hết hạn
5. Click "In chứng chỉ" để xuất PDF (cần cấu hình ir.actions.report)
```

### Chăm sóc học viên

```
1. Sau khi nhập học, tạo kế hoạch chăm sóc:
   Chăm sóc → Kế hoạch chăm sóc → Tạo mới
   Chọn loại: Welcome / Giữa khoá / Pre-exam / Upsell…

2. Khi thực hiện chăm sóc:
   → Tạo Log tương tác (edu.care.activity)
   → Ghi kết quả: Tích cực / Nguy cơ nghỉ / Upsell thành công
   → Đặt ngày follow-up tiếp theo

3. Thu thập phản hồi:
   Chăm sóc → Phản hồi & Khảo sát
   → NPS 0–10 → Tự phân loại Promoter/Passive/Detractor
```

---

## 12. Tuỳ chỉnh & Mở rộng

### Thêm loại chứng chỉ mới

Vào **Cấu hình → Mẫu chứng chỉ → Tạo mới**, chọn loại và cấu hình `ir.actions.report` để in.

### Thêm kênh tuyển sinh

Chỉnh `admission_channel` trong `edu_admission.py`:

```python
admission_channel = fields.Selection(selection=[
    ('website',   'Website'),
    ('facebook',  'Facebook'),
    # Thêm kênh mới ở đây:
    ('tiktok',    'TikTok'),
    ...
])
```

### Tích hợp thanh toán online

Liên kết `sale_order_id` trên `edu.admission` với module `payment` của Odoo để xử lý thanh toán tự động qua cổng VNPAY / MoMo / PayOS.

### Gửi thông báo tự động

Sử dụng **Automated Actions** (`Settings → Technical → Automation`) để gửi email/SMS:
- Khi hồ sơ chuyển sang `enrolled`
- Khi còn N ngày đến ngày khai giảng
- Khi học viên vắng quá X buổi

### Báo cáo & Dashboard

Tạo thêm `ir.actions.report` (QWeb PDF) cho:
- Bảng điểm học viên
- Danh sách lớp học
- Báo cáo tuyển sinh theo tháng

Hoặc dùng **Odoo Spreadsheet** (Enterprise) / kết nối **Metabase** để làm dashboard.

---

## Thông tin liên hệ

- **Tác giả**: Viettotal
- **Website**: https://viettotal.com
- **License**: LGPL-3
- **Tương thích**: Odoo 19.0 Community
