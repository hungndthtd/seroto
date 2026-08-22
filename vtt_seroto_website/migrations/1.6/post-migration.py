# -*- coding: utf-8 -*-
# code (Mã phiếu) vừa được bổ sung trên seroto.course.registration - backfill cho các
# phiếu đã tồn tại từ trước, giữ đúng định dạng "PDK<id>" đã dùng từ đầu (không đổi so
# với những gì đã từng hiển thị/gửi payOS cho các phiếu này).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    registrations = env['seroto.course.registration'].search([('code', '=', False)])
    for rec in registrations:
        rec.code = 'PDK%s' % rec.id
