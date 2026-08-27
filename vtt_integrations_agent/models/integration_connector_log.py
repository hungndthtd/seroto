# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class IntegrationConnectorLog(models.Model):
    _name = 'integration.connector.log'
    _description = 'Nhật ký kiểm tra kết nối tích hợp'
    _order = 'create_date desc'
    _rec_name = 'connector_id'

    connector_id = fields.Many2one(
        'integration.connector', string='Kết nối', required=True, ondelete='cascade',
    )
    ok = fields.Boolean(string='Thành công')
    message = fields.Char(string='Thông báo')

    @api.model
    def create_log(self, connector, ok, message):
        """TỰ NUỐT lỗi (chỉ log server, không raise) - bản thân việc ghi log không được
        phép làm hỏng luồng kiểm tra/làm mới token đang chạy, giống quy ước zalo.zns.log
        (module vtt_zalo).
        """
        try:
            return self.sudo().create({
                'connector_id': connector.id,
                'ok': ok,
                'message': message,
            })
        except Exception:
            _logger.exception('Không ghi được Nhật ký kiểm tra kết nối cho %s', connector.name)
            return self.browse()
