from odoo import http, _
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import consteq


class BankMockController(http.Controller):

    def _get_transaction_or_raise(self, tx_id, token):
        try:
            tx_id = int(tx_id)
        except (TypeError, ValueError):
            tx_id = None

        transaction = (
            request.env['bank.mock.transaction'].sudo().browse(tx_id).exists()
            if tx_id else request.env['bank.mock.transaction']
        )

        if not transaction or not token or not consteq(transaction.checkout_token, token):
            raise UserError(_('Giao dịch không hợp lệ hoặc đã bị xóa.'))

        return transaction

    # Trang "cổng thanh toán ngân hàng" giả lập - khách mở qua checkout_url
    # (bank.mock.transaction._get_checkout_url()) để "thanh toán".
    @http.route(
        '/bank-mock/checkout/<int:tx_id>/<string:token>',
        type='http', auth='public', website=True, sitemap=False,
    )
    def checkout(self, tx_id, token, **kwargs):
        transaction = request.env['bank.mock.transaction'].sudo().browse(tx_id).exists()

        if not transaction or not consteq(transaction.checkout_token, token):
            return request.not_found()

        return request.render('vtt_bank_mock.checkout_page', {'transaction': transaction})

    @http.route(
        '/bank-mock/checkout/<int:tx_id>/<string:token>/confirm',
        type='jsonrpc', auth='public', website=True,
    )
    def confirm(self, tx_id, token, **kwargs):
        transaction = self._get_transaction_or_raise(tx_id, token)
        transaction.action_confirm()
        return {'status': transaction.status}
