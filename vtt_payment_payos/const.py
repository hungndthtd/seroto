# -*- coding: utf-8 -*-

# payOS bắt buộc orderCode là số nguyên, KHÔNG được tái dùng cho lần thử thanh toán khác.
# Dùng CHUNG đúng 1 ir.sequence với vtt_payos (payos.transaction.order_code, đã khai ở
# vtt_payos/data/ir_sequence_data.xml) thay vì tự tạo sequence riêng - cả giao dịch tạo từ
# wizard cũ (vtt_payos) lẫn từ Shop (module này) cùng "rút số" nối tiếp nhau từ 1 nguồn duy
# nhất, không cần offset/khoảng cách nào để tránh trùng - xem
# models/payment_transaction.py, _payos_create_payment_link.
PAYOS_ORDER_CODE_SEQUENCE = 'payos.transaction.order_code'
