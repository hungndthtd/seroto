# -*- coding: utf-8 -*-
"""Gọi HTTP thật tới Hub trung tâm (module vtt_integrations, cài ở site KHÁC) để đẩy báo
cáo trạng thái kết nối - tách riêng, giống quy ước tools/zalo_client.py, tools/payos_client.py.

Endpoint /integration_hub/report nhận JSON THUẦN (không phải JSON-RPC envelope) vì đây là
webhook máy-gọi-máy đơn giản, không đi qua lớp RPC JS của Odoo - xem controllers/
integration_hub_controller.py bên module vtt_integrations.
"""

import requests

_TIMEOUT = 10


def push_report(hub_url, api_key, payload):
    """POST 1 báo cáo trạng thái kết nối về Hub. Ném lỗi nguyên xi (mất mạng, Hub trả lỗi)
    nếu thất bại - bên gọi (_push_report_to_hub) tự bắt + nuốt lỗi, không được để lỗi ở đây
    làm hỏng luồng kiểm tra cục bộ đang chạy.
    """
    url = hub_url.rstrip('/') + '/integration_hub/report'
    data = dict(payload)
    data['api_key'] = api_key
    resp = requests.post(url, json=data, timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def get_pending_tasks(hub_url, api_key):
    """Lấy danh sách Nhiệm vụ từ xa đang chờ (VD Kỹ thuật bấm "Làm mới Token" từ xa cho
    site này trên Dashboard Hub) - trả về list[dict] {id, provider_type, action}.
    """
    url = hub_url.rstrip('/') + '/integration_hub/pending_tasks'
    resp = requests.get(url, params={'api_key': api_key}, timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp.json().get('tasks', [])


def report_task_result(hub_url, api_key, task_id, ok, message):
    """Báo kết quả thực thi 1 Nhiệm vụ từ xa về Hub - hoàn tất vòng lặp 2 chiều
    (Hub tạo lệnh -> Agent thực thi tại chỗ -> Agent báo kết quả ngược lại)."""
    url = hub_url.rstrip('/') + '/integration_hub/task_result'
    data = {'api_key': api_key, 'task_id': task_id, 'ok': ok, 'message': message}
    resp = requests.post(url, json=data, timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp.json()
