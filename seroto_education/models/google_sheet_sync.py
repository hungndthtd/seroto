# -*- coding: utf-8 -*-

import base64
import json
import logging
import re
import time
import unicodedata
import urllib.parse

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from odoo import api, models

_logger = logging.getLogger(__name__)

GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_SHEETS_READONLY_SCOPE = 'https://www.googleapis.com/auth/spreadsheets.readonly'

# Khớp cột theo TỪ KHÓA trong dòng tiêu đề (row 1) - không phụ thuộc thứ tự/vị trí cột,
# vẫn chạy đúng nếu form đổi thứ tự câu hỏi hoặc thêm/bớt cột khác. So khớp trên chuỗi đã
# bỏ dấu + viết thường (xem _normalize_header) nên không bị lỗi lệch encode dấu tiếng Việt
# (NFC/NFD) từng gặp phải khi so khớp nguyên văn có dấu. KHÔNG cần khớp cột "khóa học" nữa
# - mỗi Spreadsheet ở đây gắn cứng 1-1 với 1 Lớp học (academic.class), khóa học lấy thẳng
# từ class_id.course_id, không đọc từ dữ liệu trong Sheet.
_FIELD_HEADER_PATTERNS = [
    ('phone', ('dien thoai', 'so dien thoai', 'sdt', 'phone')),
    ('email', ('email', 'dia chi email')),
    ('name', ('ho va ten', 'ho ten', 'ten hoc vien', 'full name', 'ten')),
]


_SPREADSHEET_URL_RE = re.compile(r'/spreadsheets/d/([a-zA-Z0-9_-]+)')
_COL_LETTER_RE = re.compile(r'^[A-Za-z]+$')


def _extract_spreadsheet_id(url):
    """Lớp học lưu NGUYÊN link Sheet (field google_sheet_url) để bấm nhảy được sang Sheet
    trên form - tách lấy đúng Spreadsheet ID cần cho Google Sheets API ở đây."""
    match = _SPREADSHEET_URL_RE.search(url or '')
    return match.group(1) if match else (url or '').strip()


def _col_letter_to_index(letter):
    """Đổi ký hiệu cột kiểu Google Sheet (A, B, ..., Z, AA, AB, ...) sang index 0-based
    (A=0, B=1, ..., Z=25, AA=26, ...) - dùng cho field chỉ định cột tay
    (google_sheet_col_name/phone/email trên academic.class)."""
    letter = (letter or '').strip().upper()
    if not _COL_LETTER_RE.match(letter):
        raise ValueError(f'Ký hiệu cột không hợp lệ: "{letter}" (phải dạng chữ cái, vd "A", "AP").')
    index = 0
    for char in letter:
        index = index * 26 + (ord(char) - ord('A') + 1)
    return index - 1


def _normalize_header(text):
    text = (text or '').strip().lower()
    # "đ" không phải chữ có dấu ghép base+combining-mark nên NFKD KHÔNG decompose nó
    # (khác với các nguyên âm ệ/ạ/...) - encode ascii-ignore sẽ XÓA MẤT "đ" thay vì trả
    # về "d" nếu không tự thay trước (vd "điện thoại" sẽ thành "ien thoai" chứ không
    # phải "dien thoai", làm sai lệch toàn bộ so khớp từ khóa).
    text = text.replace('đ', 'd')
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')


class GoogleSheetSync(models.AbstractModel):
    _name = 'google.sheet.sync'
    _description = 'Đồng bộ định kỳ: đọc đăng ký mới từ Google Sheet (mỗi Lớp học 1 Spreadsheet riêng) vào CRM Lead'

    # =====================================================
    # 1. Lấy access token bằng Service Account (JWT Bearer flow, tự ký JWT bằng
    #    "cryptography" - thư viện Odoo core đã có sẵn, không cần cài thêm
    #    google-auth/google-api-python-client). Dùng CHUNG 1 token cho mọi Lớp học
    #    trong 1 lượt chạy cron (cùng 1 Service Account đọc nhiều Spreadsheet khác nhau).
    # =====================================================
    def _get_access_token(self):
        ICP = self.env['ir.config_parameter'].sudo()
        client_email = ICP.get_param('seroto_education.google_sa_client_email')
        private_key_pem = ICP.get_param('seroto_education.google_sa_private_key')

        if not client_email or not private_key_pem:
            raise ValueError(
                'Chưa cấu hình Service Account: cần set 2 System Parameters '
                '"seroto_education.google_sa_client_email" và '
                '"seroto_education.google_sa_private_key".'
            )

        # Lỗi copy-paste rất thường gặp: dán nguyên chuỗi "private_key" từ file JSON
        # tải về, trong đó xuống dòng được ghi dưới dạng 2 ký tự "\n" (đúng cú pháp
        # JSON) thay vì ký tự xuống dòng thật - PEM parser cần xuống dòng thật nên tự
        # chuẩn hóa lại ở đây, không bắt phải paste đúng định dạng nhiều dòng.
        private_key_pem = private_key_pem.replace('\\n', '\n')

        now = int(time.time())
        header = {'alg': 'RS256', 'typ': 'JWT'}
        claims = {
            'iss': client_email,
            'scope': GOOGLE_SHEETS_READONLY_SCOPE,
            'aud': GOOGLE_TOKEN_URL,
            'iat': now,
            'exp': now + 3600,
        }

        def b64url(data):
            return base64.urlsafe_b64encode(data).rstrip(b'=')

        signing_input = (
            b64url(json.dumps(header).encode()) + b'.' + b64url(json.dumps(claims).encode())
        )

        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(), password=None,
        )
        signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())

        jwt_assertion = (signing_input + b'.' + b64url(signature)).decode()

        resp = requests.post(GOOGLE_TOKEN_URL, data={
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'assertion': jwt_assertion,
        }, timeout=15)
        resp.raise_for_status()
        return resp.json()['access_token']

    def _sheets_get(self, token, sheet_id, range_a1):
        """GET 1 range trong Sheet, tự bọc dấu nháy đơn quanh tên tab + URL-encode (path
        URL không tự encode như query params) - dùng chung cho đọc header lẫn dữ liệu.
        """
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{urllib.parse.quote(range_a1, safe='')}"
        resp = requests.get(url, headers={'Authorization': f'Bearer {token}'}, timeout=15)
        if resp.status_code != 200:
            _logger.error('Google Sheets API trả lỗi %s cho range "%s": %s', resp.status_code, range_a1, resp.text)
        resp.raise_for_status()
        return resp.json().get('values', [])

    def _resolve_sheet_tab(self, token, sheet_id, sheet_tab):
        """Nếu Lớp học không chỉ định tên tab, tự lấy tab ĐẦU TIÊN trong Spreadsheet qua
        API lấy metadata - đúng cho hầu hết trường hợp vì mỗi Spreadsheet ở đây thường
        chỉ có 1 tab response.
        """
        if sheet_tab:
            return sheet_tab
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}"
        resp = requests.get(
            url, headers={'Authorization': f'Bearer {token}'},
            params={'fields': 'sheets.properties.title'}, timeout=15,
        )
        if resp.status_code != 200:
            _logger.error('Google Sheets API trả lỗi %s khi lấy danh sách tab: %s', resp.status_code, resp.text)
        resp.raise_for_status()
        sheets = resp.json().get('sheets', [])
        if not sheets:
            raise ValueError(f'Spreadsheet "{sheet_id}" không có tab nào.')
        return sheets[0]['properties']['title']

    def _get_column_map(self, token, sheet_id, sheet_tab):
        """Đọc dòng tiêu đề (row 1), khớp theo từ khóa (xem _FIELD_HEADER_PATTERNS) để
        tìm đúng cột name/email/phone - linh động theo tên cột thật trong Sheet, không
        cần cố định vị trí/thứ tự cột.
        """
        values = self._sheets_get(token, sheet_id, f"'{sheet_tab}'!1:1")
        headers = values[0] if values else []

        column_map = {}
        for col_index, raw_header in enumerate(headers):
            normalized = _normalize_header(raw_header)
            if not normalized:
                continue
            for field, keywords in _FIELD_HEADER_PATTERNS:
                if field in column_map:
                    continue
                if any(kw in normalized for kw in keywords):
                    column_map[field] = col_index
                    break

        missing = [f for f in ('name', 'phone') if f not in column_map]
        if missing:
            raise ValueError(
                f"Không tìm thấy cột khớp với {missing} trong dòng tiêu đề Sheet "
                f"(dòng 1 hiện tại: {headers}). Kiểm tra lại tên cột trong Google Sheet, "
                f"hoặc chỉ định tay ký hiệu cột trong form Lớp học."
            )
        return column_map

    def _resolve_column_map(self, token, sheet_id, sheet_tab, class_rec):
        """Nếu Lớp học đã chỉ định TAY ký hiệu cột (google_sheet_col_name/phone/email),
        dùng đúng cột đó - KHÔNG đoán tự động nữa (an toàn tuyệt đối khi Sheet có nhiều
        cột dễ gây nhầm, vd vừa có "SĐT đại diện nhóm" vừa có "SĐT (Zalo)" của chính người
        đăng ký). Chỉ quay lại đoán tự động theo từ khóa tiêu đề khi để trống CẢ 3.
        """
        manual_cols = {
            'name': class_rec.google_sheet_col_name,
            'phone': class_rec.google_sheet_col_phone,
            'email': class_rec.google_sheet_col_email,
        }
        if not any(manual_cols.values()):
            return self._get_column_map(token, sheet_id, sheet_tab)

        column_map = {}
        for field, letter in manual_cols.items():
            if letter:
                column_map[field] = _col_letter_to_index(letter)

        missing = [f for f in ('name', 'phone') if f not in column_map]
        if missing:
            raise ValueError(
                f'Lớp "{class_rec.name}" đã chỉ định tay 1 số cột nhưng còn thiếu cột '
                f'{missing} - cần điền đủ ký hiệu cột "Họ và tên" và "Số điện thoại" '
                f'trong form Lớp học (hoặc xóa hết để quay lại tự đoán theo tiêu đề).'
            )
        return column_map

    # =====================================================
    # 2. Đọc các dòng MỚI từ 1 Spreadsheet gắn với 1 Lớp học (từ dòng đã đồng bộ lần
    #    trước + 1 trở đi)
    # =====================================================
    def _fetch_new_rows(self, token, class_rec):
        sheet_id = _extract_spreadsheet_id(class_rec.google_sheet_url)
        sheet_tab = self._resolve_sheet_tab(token, sheet_id, class_rec.google_sheet_tab)
        last_row = class_rec.google_sheet_last_row or 1

        column_map = self._resolve_column_map(token, sheet_id, sheet_tab, class_rec)

        # Đọc rộng tới cột Z (thay vì cố định A:E) để không phụ thuộc Sheet có bao nhiêu
        # cột hay thứ tự cột - vị trí thật của từng field đã biết qua column_map.
        values = self._sheets_get(token, sheet_id, f"'{sheet_tab}'!A{last_row + 1}:Z")

        def get_col(raw_row, field):
            idx = column_map.get(field)
            if idx is None or idx >= len(raw_row):
                return ''
            return (raw_row[idx] or '').strip()

        rows = []
        for i, raw_row in enumerate(values):
            rows.append({
                'row_number': last_row + 1 + i,
                'name': get_col(raw_row, 'name'),
                'email': get_col(raw_row, 'email'),
                'phone': get_col(raw_row, 'phone'),
            })
        return rows

    # =====================================================
    # 3. Tạo/cập nhật Contact + CRM Lead cho 1 dòng của 1 Lớp học - cùng logic dedupe
    #    Contact với route /api/google_form/lead (webhook) trước đây, chỉ khác nguồn dữ
    #    liệu đầu vào. Khóa học/Lớp học lấy THẲNG từ class_rec, không đọc từ Sheet.
    # =====================================================
    def _process_row(self, class_rec, row):
        # Định danh duy nhất theo cả Lớp học lẫn số dòng - bắt buộc phải có id Lớp học
        # trong đây vì số dòng tự nó có thể trùng giữa các Spreadsheet khác nhau.
        row_ref = f"{class_rec.id}:{row['row_number']}"
        name = row['name']
        phone = row['phone']
        email = row['email']

        if not name or not phone:
            _logger.warning(
                'Lớp "%s" - Sheet dòng %s thiếu tên/SĐT, bỏ qua: %s',
                class_rec.name, row['row_number'], row,
            )
            return

        # An toàn bổ sung: nếu vì lý do gì đó dòng này đã được xử lý trước đó (vd cron
        # bị crash giữa lúc tạo lead xong nhưng chưa kịp lưu "last_row" tiến độ), không
        # tạo trùng lead nữa.
        existing = self.env['crm.lead'].sudo().search(
            [('google_sheet_row_ref', '=', row_ref)], limit=1
        )
        if existing:
            return

        Partner = self.env['res.partner'].sudo()
        partner = email and Partner.search([('email', '=', email)], limit=1)
        if not partner:
            partner = Partner.search([('phone', '=', phone)], limit=1)
        if not partner:
            partner = Partner.create({'name': name, 'email': email, 'phone': phone})

        source = self.env['utm.source'].sudo().search([('name', '=', 'Google Form')], limit=1)
        if not source:
            source = self.env['utm.source'].sudo().create({'name': 'Google Form'})

        self.env['crm.lead'].sudo().create({
            'name': f"[Google Form] {name} - {class_rec.name}",
            'contact_name': name,
            'partner_id': partner.id,
            'email_from': email,
            'phone': phone,
            'course_id': class_rec.course_id.id,
            'class_id': class_rec.id,
            'source_id': source.id,
            'google_sheet_row_ref': row_ref,
            'description': (
                f"Đăng ký qua Google Form (đồng bộ định kỳ từ Google Sheet).\n"
                f"Lớp học: {class_rec.name}\nKhóa học: {class_rec.course_id.name}"
            ),
        })

    # =====================================================
    # 4. Entry point cho ir.cron (Scheduled Action) - xem data/google_sheet_sync_cron.xml.
    #    Lặp qua TẤT CẢ Lớp học (đang active) có khai báo Spreadsheet ID - mỗi Lớp lỗi
    #    riêng không làm hỏng các Lớp còn lại (log lỗi rồi tiếp tục lớp kế tiếp).
    # =====================================================
    @api.model
    def cron_sync_google_form_leads(self):
        try:
            token = self._get_access_token()
        except Exception:
            _logger.exception('Lỗi khi lấy access token Google - dừng toàn bộ đồng bộ')
            return

        classes = self.env['academic.class'].sudo().search([
            ('active', '=', True),
            ('google_sheet_url', '!=', False),
            # Bắt buộc nhân viên tự tick xác nhận đã cấu hình xong (link + cột) trước khi
            # cron mới bắt đầu đồng bộ Lớp này - tránh trường hợp dán link/điền cột dở
            # dang mà cron đã chạy nhầm, tạo sai Lead/Contact.
            ('google_sheet_sync_confirmed', '=', True),
        ])

        total_processed = 0
        for class_rec in classes:
            try:
                rows = self._fetch_new_rows(token, class_rec)
            except Exception:
                _logger.exception('Lỗi khi đọc dữ liệu Google Sheet cho lớp "%s"', class_rec.name)
                continue

            # Đọc thành công (dù có dòng mới hay không) - ghi lại ĐÚNG ID Spreadsheet đang
            # đồng bộ để write() trên academic.class biết "last_row" này ứng với sheet nào,
            # tự reset đúng lúc nếu sau này link đổi sang Spreadsheet khác (xem
            # models/academic_class.py).
            class_rec.google_sheet_synced_id = _extract_spreadsheet_id(class_rec.google_sheet_url)

            processed = 0
            for row in rows:
                try:
                    self._process_row(class_rec, row)
                except Exception:
                    # Dừng lại tại dòng lỗi của LỚP NÀY - KHÔNG cập nhật last_row vượt
                    # qua dòng này, để lần cron kế tiếp tự thử lại đúng dòng bị lỗi thay
                    # vì bỏ sót vĩnh viễn. Các lớp khác vẫn tiếp tục xử lý bình thường.
                    _logger.exception(
                        'Lỗi khi xử lý dòng Sheet %s của lớp "%s", dừng đồng bộ lớp này đợt này',
                        row['row_number'], class_rec.name,
                    )
                    break
                else:
                    class_rec.google_sheet_last_row = row['row_number']
                    processed += 1

            if processed:
                total_processed += processed
                _logger.info('Lớp "%s": đã xử lý %s dòng mới từ Google Sheet', class_rec.name, processed)

        if total_processed:
            _logger.info('Đồng bộ Google Sheet -> CRM Lead: tổng cộng %s dòng mới', total_processed)
