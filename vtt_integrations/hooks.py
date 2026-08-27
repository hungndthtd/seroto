# -*- coding: utf-8 -*-
"""post_init_hook: tự gán Website mặc định (integration_website_default, xem
data/integration_website_data.xml) cho các kết nối CỤC BỘ (is_remote=False) còn thiếu
client_site_id - chạy tự động mỗi lần cài/nâng cấp module, thay cho việc phải tự gán tay qua
shell như lúc mới thêm field này.
"""


def assign_default_website(env):
    website = env.ref('vtt_integrations.integration_website_default', raise_if_not_found=False)
    if not website:
        return
    connectors = env['integration.connector'].search([
        ('client_site_id', '=', False), ('is_remote', '=', False),
    ])
    if connectors:
        connectors.write({'client_site_id': website.id})
