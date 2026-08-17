/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

// Trang "cổng thanh toán ngân hàng" giả lập (views/bank_mock_views.xml,
// template checkout_page) - nút Xác nhận chỉ gọi RPC rồi tải lại trang để hiện đúng
// trạng thái mới (server đã tự gọi webhook báo cho bên tạo giao dịch trong lúc xử lý
// RPC, xem models/bank_transaction.py _notify()).
publicWidget.registry.BankMockCheckout = publicWidget.Widget.extend({

    selector: "#bank_mock_checkout_root",

    events: {
        "click #bank_mock_confirm_btn": "_onConfirm",
    },

    async _onConfirm(ev) {
        const btn = ev.currentTarget;
        btn.disabled = true;
        const { txId, txToken } = this.el.dataset;

        try {
            await rpc(`/bank-mock/checkout/${txId}/${txToken}/confirm`, {});
        } catch (error) {
            console.error("Bank mock confirm failed:", error);
            alert("Có lỗi xảy ra, vui lòng thử lại.");
            btn.disabled = false;
            return;
        }

        window.location.reload();
    },

});
