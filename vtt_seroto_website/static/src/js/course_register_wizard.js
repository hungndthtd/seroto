/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

const POLL_INTERVAL_MS = 3000;

// Widget cho modal đăng ký khóa học DẠNG NHIỀU BƯỚC (wizard) gắn trên
// views/course_register_wizard.xml + trang xem phiếu qua link email
// (views/course_registration_slip_page.xml).
//
// Tab "Thông tin cơ bản" hoàn tất -> gọi RPC tạo bản ghi seroto.course.registration +
// link thanh toán payOS thật (module vtt_payos) + gửi email kèm link phiếu (xem
// controllers/course_registration.py). Ảnh QR (qrUrl) do SERVER sinh sẵn từ đúng chuỗi
// VietQR payOS trả về (không tự suy từ checkoutUrl như bản giả lập trước đây - checkoutUrl
// chỉ là link mở trang thanh toán, không phải mã QR chuyển khoản thật). Tab "Thanh toán"
// mở trang thanh toán payOS ở tab mới rồi POLLING (setInterval, không dùng WebSocket/
// longpolling cho đơn giản) để tự phát hiện lúc webhook payOS báo đã thanh toán - KHÔNG
// có nút tự khai "Tôi đã thanh toán".
//
// Cố tình KHÔNG tái sử dụng "register-course"/register_modal.js (seroto_form) - trigger
// ở đây là class riêng "js_register_course_wizard" để không ảnh hưởng modal đăng ký 1
// bước đang dùng ở các trang/snippet khác.
publicWidget.registry.CourseRegisterWizard = publicWidget.Widget.extend({

    selector: "#wrapwrap",

    events: {
        "click .js_register_course_wizard": "_onOpenWizard",
        "click .course_wizard_step": "_onStepClick",
        "input #course_wizard_basic_form": "_onBasicInput",
        "change select[name='student_relation']": "_onRelationChange",
        "change #wizard_registration_category": "_onCategoryChange",
        "submit #course_wizard_basic_form": "_onBasicSubmit",
        "click #wizard_payment_continue": "_onWizardPaymentContinue",
        "click #wizard_open_slip_unpaid": "_onOpenSlipFromWizard",
        "submit #course_wizard_detail_form": "_onDetailSubmit",
        "submit #slip_page_questions_form": "_onSlipQuestionsSubmit",
    },

    start() {
        this._state = this._emptyState();
        this._pollTimer = null;

        // Trang xem phiếu qua link email (views/course_registration_slip_page.xml) -
        // KHÔNG đi qua wizard nên không có trong this._state, cần tự polling riêng nếu
        // đang ở trạng thái chưa thanh toán. Chỉ polling khi #slip_page_payment_section
        // thật sự có mặt - phiếu rejected/cancelled hoặc đã thanh toán không render khối
        // này (xem template), dù #course_registration_slip_page_root luôn render.
        const slipPageRoot = this.el.querySelector("#course_registration_slip_page_root");
        if (slipPageRoot && this.el.querySelector("#slip_page_payment_section")) {
            this._pollSlipPage(slipPageRoot);
        }

        return this._super(...arguments);
    },

    destroy() {
        this._clearPollTimer();
        if (this._slipPagePollTimer) {
            clearInterval(this._slipPagePollTimer);
        }
        return this._super(...arguments);
    },

    _emptyState() {
        return {
            registrationId: null,
            accessToken: null,
            checkoutUrl: null,
            qrUrl: null,
            course: "", name: "", email: "", phone: "",
            studentRelation: "self", studentName: "",
            questions: [], // [{id, question}, ...] - riêng theo từng khóa học, xem _renderQuestions()
            answers: [], // [{question, answer}, ...] - đã lưu ở Tab 3
            paid: false,
        };
    },

    // --- Mở wizard từ nút "Đăng ký ngay" ---
    // async: kiểm tra is_registration_open TRƯỚC khi mở modal - áp dụng cho MỌI nút
    // js_register_course_wizard trên toàn site (kể cả nút tĩnh ở trang con không có
    // widget riêng tự ẩn/hiện như s_trang_chu_course_group), tránh để khách điền hết
    // form 3 bước rồi mới nhận lỗi thô ở bước cuối (server vẫn chặn lại ở
    // create_registration() - đây chỉ là lớp chặn sớm, thân thiện hơn).
    async _onOpenWizard(ev) {
        ev.preventDefault();

        const course = ev.currentTarget.dataset.course || "";

        let openCheck;
        try {
            openCheck = await rpc("/seroto/academic-course/is-registration-open", { course });
        } catch (error) {
            // Lỗi mạng/route tạm thời - không chặn nhầm khách, để server tự chặn lại ở
            // bước tạo phiếu nếu thật sự đang đóng (xem catch trong _onBasicSubmit).
            console.error("Kiểm tra trạng thái mở đăng ký thất bại:", error);
            openCheck = { is_registration_open: true };
        }
        if (!openCheck.is_registration_open) {
            alert(`Khóa học "${course}" hiện chưa mở đăng ký, vui lòng quay lại sau hoặc liên hệ Seroto để được tư vấn.`);
            return;
        }

        this._clearPollTimer();

        this._state = this._emptyState();
        this._state.course = course;

        const modalEl = this.el.querySelector("#courseRegisterWizardModal");

        modalEl.querySelector("#course_wizard_basic_form").reset();
        modalEl.querySelector("#course_wizard_detail_form").reset();
        modalEl.querySelector("#course_wizard_questions_container").replaceChildren();
        modalEl.querySelector("#wizard_course_name").value = this._state.course;
        // form.reset() đưa radio "Đăng ký cho" về lại "Bản thân" (mặc định checked
        // trong HTML), nhưng không tự ẩn khối field học viên (chỉ là class CSS, không
        // phải state của form) - phải tự ẩn lại tay ở đây.
        modalEl.querySelector("#wizard_student_fields").classList.add("d-none");
        modalEl.querySelector("[name='student_name']").required = false;
        // Diện đăng ký - form.reset() đưa <select> về lại "tuition" (option mặc định
        // trong HTML) nhưng KHÔNG tự ẩn/hiện lại các khối field theo diện (chỉ là class
        // CSS, không phải state của form) - tự làm lại y hệt _onCategoryChange cho diện
        // mặc định, giống cách #wizard_student_fields đang tự re-hide ở trên. Diện đóng
        // học phí (mặc định) không có khối riêng nào cần hiện.
        ["voucher", "upload", "medical", "nonprofit"].forEach((name) => {
            modalEl.querySelector(`#wizard_category_${name}_fields`).classList.add("d-none");
        });
        modalEl.querySelector("#wizard_category_attachment_input").value = "";
        modalEl.querySelector("#wizard_email_sent_note").textContent = "";
        modalEl.querySelector("#wizard_payment_pending").classList.remove("d-none");
        modalEl.querySelector("#wizard_payment_success").classList.add("d-none");

        // Đăng ký mới -> chỉ bước 1 được mở, khoá lại 2 nút bước còn lại dù trước đó
        // (course khác) đã mở tới đâu.
        modalEl.querySelectorAll(".course_wizard_step").forEach((btn) => {
            btn.disabled = btn.dataset.step !== "basic";
        });
        this._showPane(modalEl, "basic");
        this._updateBasicContinueState(modalEl);

        $(modalEl).modal("show");
    },

    // Nút bước đang "disabled" không bao giờ phát sinh sự kiện click (hành vi mặc định
    // của <button disabled>) - nên hàm này chỉ chạy khi bấm vào bước ĐÃ mở khoá, tự
    // nhiên chặn được yêu cầu "không click tab được" cho các bước chưa hoàn tất.
    _onStepClick(ev) {
        const modalEl = ev.currentTarget.closest(".modal");
        this._showPane(modalEl, ev.currentTarget.dataset.step);
    },

    // --- Tab 1: Thông tin cơ bản ---
    _onBasicInput(ev) {
        this._updateBasicContinueState(ev.currentTarget.closest(".modal"));
    },

    _updateBasicContinueState(modalEl) {
        const form = modalEl.querySelector("#course_wizard_basic_form");
        modalEl.querySelector("#wizard_basic_continue").disabled = !form.checkValidity();
    },

    // "Đăng ký cho": Bản thân -> ẩn khối chọn mối quan hệ/họ tên học viên, không bắt
    // buộc. Người thân -> hiện khối đó, bắt buộc phải điền họ tên học viên.
    _onRelationChange(ev) {
        const modalEl = ev.currentTarget.closest(".modal");
        const fieldsEl = modalEl.querySelector("#wizard_student_fields");
        const studentNameInput = modalEl.querySelector("[name='student_name']");
        const isOther = ev.currentTarget.value === "other";

        fieldsEl.classList.toggle("d-none", !isOther);
        studentNameInput.required = isOther;
        if (!isOther) {
            studentNameInput.value = "";
        }
        this._updateBasicContinueState(modalEl);
    },

    // "Diện đăng ký": hiện đúng (các) khối field theo diện đã chọn - medical/nonprofit
    // hiện CẢ khối riêng LẪN khối "upload" dùng chung (3 diện cần nộp giấy tờ). Đúng
    // pattern _onRelationChange, chỉ áp dụng cho nhiều khối hơn 1.
    _onCategoryChange(ev) {
        const modalEl = ev.currentTarget.closest(".modal");
        const category = ev.currentTarget.value;

        // Diện đóng học phí không có khối riêng nào trên website (xem
        // views/course_register_wizard.xml) - "Trạng thái đăng ký" chỉ nhân viên tự
        // chọn tay trên backend.
        const BLOCKS_BY_CATEGORY = {
            tuition: [],
            voucher: ["voucher"],
            education_scholarship: ["upload"],
            medical_scholarship: ["medical", "upload"],
            nonprofit: ["nonprofit", "upload"],
        };
        const visibleBlocks = BLOCKS_BY_CATEGORY[category] || [];

        ["voucher", "upload", "medical", "nonprofit"].forEach((name) => {
            const blockEl = modalEl.querySelector(`#wizard_category_${name}_fields`);
            const isVisible = visibleBlocks.includes(name);
            blockEl.classList.toggle("d-none", !isVisible);
            if (!isVisible) {
                // Ẩn thì xóa luôn giá trị (kể cả file đã chọn) - tránh gửi lên field
                // của diện KHÔNG còn được chọn nữa.
                blockEl.querySelectorAll("input, select").forEach((input) => {
                    if (input.tagName === "SELECT") {
                        input.selectedIndex = 0;
                    } else {
                        input.value = "";
                    }
                });
            }
        });

        // Khối "upload" dùng chung cho 3 diện - đổi hint/link tải mẫu tùy diện đang
        // chọn (medical_scholarship không có mẫu sẵn của Seroto để tải).
        const UPLOAD_HINTS = {
            education_scholarship: "Vui lòng đính kèm giấy xác nhận của trường (có thể dùng mẫu của Seroto).",
            medical_scholarship: "Vui lòng đính kèm thẻ đeo (thẻ nhân viên, thẻ chức danh...) hoặc giấy tờ chứng minh khác.",
            nonprofit: "Vui lòng đính kèm giấy xác nhận của tổ chức (có thể dùng mẫu của Seroto).",
        };
        modalEl.querySelector("#wizard_category_upload_hint").textContent = UPLOAD_HINTS[category] || "";
        modalEl.querySelector("#wizard_category_template_link").classList.toggle(
            "d-none", category !== "education_scholarship" && category !== "nonprofit",
        );

        this._updateBasicContinueState(modalEl);
    },

    // Đọc 1 File thành {filename, data (base64, không kèm tiền tố "data:...;base64,"),
    // mimetype} - dùng để gửi kèm JSON-RPC (route hiện tại là jsonrpc thuần, không phải
    // multipart/form-data, nên phải encode base64 thay vì gửi file thẳng).
    _fileToAttachment(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
                const result = reader.result || "";
                const base64 = result.includes(",") ? result.split(",")[1] : result;
                resolve({ filename: file.name, data: base64, mimetype: file.type });
            };
            reader.onerror = () => reject(reader.error);
            reader.readAsDataURL(file);
        });
    },

    async _onBasicSubmit(ev) {
        ev.preventDefault();

        const form = ev.currentTarget;
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        const modalEl = form.closest(".modal");
        const data = new FormData(form);
        const name = (data.get("name") || "").trim();
        const email = (data.get("email") || "").trim();
        const phone = (data.get("phone") || "").trim();
        const studentRelation = data.get("student_relation") || "self";
        const studentName = studentRelation === "other" ? (data.get("student_name") || "").trim() : "";
        const category = data.get("registration_category") || "tuition";
        const commitmentConfirmed = modalEl.querySelector("#wizard_commitment").checked;

        // Chỉ gửi lên field của ĐÚNG diện đang chọn - field của diện khác luôn bị
        // _onCategoryChange xóa giá trị lúc ẩn khối tương ứng, nhưng lọc lại ở đây theo
        // category cho rõ ràng, khỏi phụ thuộc hoàn toàn vào việc JS đã xóa đúng chưa.
        // Diện đóng học phí không gửi gì thêm - "Trạng thái đăng ký" (sớm/bình thường)
        // chỉ nhân viên tự chọn tay trên backend, không có ở form website.
        const categoryVals = {};
        if (category === "voucher") {
            categoryVals.voucher_type = data.get("voucher_type") || "";
            categoryVals.voucher_code = (data.get("voucher_code") || "").trim();
        } else if (category === "medical_scholarship") {
            categoryVals.medical_facility_name = (data.get("medical_facility_name") || "").trim();
            categoryVals.medical_facility_province = (data.get("medical_facility_province") || "").trim();
            categoryVals.medical_role = (data.get("medical_role") || "").trim();
        } else if (category === "nonprofit") {
            categoryVals.nonprofit_org_name = (data.get("nonprofit_org_name") || "").trim();
            categoryVals.nonprofit_org_province = (data.get("nonprofit_org_province") || "").trim();
            categoryVals.nonprofit_org_ward = (data.get("nonprofit_org_ward") || "").trim();
            categoryVals.nonprofit_registrant_role = (data.get("nonprofit_registrant_role") || "").trim();
            categoryVals.nonprofit_signer_name = (data.get("nonprofit_signer_name") || "").trim();
            categoryVals.nonprofit_signer_phone = (data.get("nonprofit_signer_phone") || "").trim();
            categoryVals.nonprofit_representative_name = (data.get("nonprofit_representative_name") || "").trim();
            categoryVals.nonprofit_representative_phone = (data.get("nonprofit_representative_phone") || "").trim();
        }

        // 3 diện cần nộp giấy tờ dùng CHUNG 1 ô chọn file - đọc + encode base64 TRƯỚC
        // khi khóa nút "Tiếp tục" (route hiện tại là jsonrpc thuần, không phải multipart,
        // nên phải gửi file dạng base64 kèm trong payload JSON).
        let attachments = [];
        const UPLOAD_CATEGORIES = ["education_scholarship", "medical_scholarship", "nonprofit"];
        if (UPLOAD_CATEGORIES.includes(category)) {
            const MAX_SIZE = 10 * 1024 * 1024;
            const files = Array.from(modalEl.querySelector("#wizard_category_attachment_input").files || []);
            const tooLarge = files.find((file) => file.size > MAX_SIZE);
            if (tooLarge) {
                alert(`File "${tooLarge.name}" vượt quá 10MB, vui lòng chọn file khác.`);
                return;
            }
            try {
                attachments = await Promise.all(files.map((file) => this._fileToAttachment(file)));
            } catch (error) {
                console.error("Đọc file đính kèm thất bại:", error);
                alert("Không đọc được file đính kèm, vui lòng thử lại.");
                return;
            }
        }

        const hasStudiedSeroto = data.get("has_studied_seroto_before") || "no";

        const continueBtn = modalEl.querySelector("#wizard_basic_continue");
        continueBtn.disabled = true;
        continueBtn.textContent = "Đang xử lý...";

        // Đã submit thành công 1 lần trước đó (registrationId đã có, VD khách bấm quay lại
        // bước 1 sửa lại rồi bấm "Tiếp tục" lần nữa) - GHI ĐÈ lên đúng phiếu cũ thay vì tạo
        // phiếu MỚI + giao dịch thanh toán MỚI mỗi lần bấm lại (xem controllers/
        // course_registration.py, update_basic_registration).
        const isUpdate = Boolean(this._state.registrationId);
        const payload = {
            course: this._state.course,
            name,
            email,
            phone,
            student_relation: studentRelation,
            student_name: studentName,
            has_studied_seroto_before: hasStudiedSeroto,
            registration_category: category,
            commitment_confirmed: commitmentConfirmed,
            attachments,
            ...categoryVals,
        };
        if (isUpdate) {
            payload.id = this._state.registrationId;
            payload.token = this._state.accessToken;
        }

        let result;
        try {
            result = await rpc(
                isUpdate
                    ? "/seroto/course-registration/update-basic"
                    : "/seroto/course-registration/create",
                payload,
            );
        } catch (error) {
            console.error(isUpdate ? "Cập nhật phiếu đăng ký thất bại:" : "Tạo phiếu đăng ký thất bại:", error);
            // error.data.message: nội dung UserError thật từ server (VD "Khóa học ...
            // hiện không mở đăng ký" - trường hợp hiếm khi khóa vừa đóng đúng lúc khách
            // đang điền form, giữa lúc mở modal và lúc bấm "Tiếp tục") - chỉ rơi về câu
            // chung chung khi đây thực sự là lỗi không xác định được (mất mạng...).
            const serverMessage = error && error.data && error.data.message;
            alert(serverMessage || "Có lỗi xảy ra, vui lòng thử lại.");
            continueBtn.textContent = "Tiếp tục";
            continueBtn.disabled = false;
            return;
        }

        this._state.registrationId = result.id;
        this._state.accessToken = result.token;
        this._state.checkoutUrl = result.checkout_url;
        this._state.qrUrl = result.qr_url;
        this._state.questions = result.questions || [];
        this._state.name = name;
        this._state.email = email;
        this._state.phone = phone;
        this._state.studentRelation = studentRelation;
        this._state.studentName = studentName;
        this._state.code = result.code;
        this._state.categoryLabel = result.registration_category_label;
        this._state.voucherLabel = result.voucher_label;
        this._state.baseAmount = result.base_amount;
        this._state.amount = result.amount;
        this._state.pendingConfirmation = result.pending_confirmation;

        this._renderQuestions(modalEl);

        continueBtn.textContent = "Tiếp tục";
        continueBtn.disabled = false;

        // Lưu vào "Phiếu đăng ký khóa học" (modal khác) rồi chuyển wizard sang tab
        // Thanh toán - đúng theo yêu cầu luồng.
        this._syncSlip();

        modalEl.querySelector('.course_wizard_step[data-step="payment"]').disabled = false;

        // Hiện đầy đủ lại thông tin đã điền ở Tab 1 + thông tin thanh toán (diện đăng ký,
        // số tiền, voucher, nội dung chuyển khoản) để khách đối chiếu lại trước khi trả
        // tiền - các ô này đều là <input readonly>, PHẢI gán .value (không phải
        // .textContent như trước lúc còn là <strong>/<p>).
        modalEl.querySelector("#wizard_payment_course").value = this._state.course;
        const isForOther = this._state.studentRelation === "other";
        modalEl.querySelector("#wizard_payment_student_row").classList.toggle("d-none", !isForOther);
        if (isForOther) {
            modalEl.querySelector("#wizard_payment_student").value = this._state.studentName;
        }
        modalEl.querySelector("#wizard_payment_name").value = this._state.name;
        modalEl.querySelector("#wizard_payment_email").value = this._state.email;
        modalEl.querySelector("#wizard_payment_phone").value = this._state.phone;
        modalEl.querySelector("#wizard_payment_category").value = this._state.categoryLabel || "";
        const voucherRow = modalEl.querySelector("#wizard_payment_voucher_row");
        voucherRow.classList.toggle("d-none", !this._state.voucherLabel);
        if (this._state.voucherLabel) {
            modalEl.querySelector("#wizard_payment_voucher").value = this._state.voucherLabel;
        }
        const baseAmount = this._state.baseAmount || 0;
        const amount = this._state.amount || 0;
        const discountAmount = baseAmount - amount;
        modalEl.querySelector("#wizard_payment_base_amount").value =
            `${baseAmount.toLocaleString("vi-VN")} ₫`;
        const discountRow = modalEl.querySelector("#wizard_payment_discount_row");
        discountRow.classList.toggle("d-none", discountAmount <= 0);
        if (discountAmount > 0) {
            modalEl.querySelector("#wizard_payment_discount_amount").value =
                `${discountAmount.toLocaleString("vi-VN")} ₫`;
        }
        modalEl.querySelector("#wizard_payment_amount").value =
            `${amount.toLocaleString("vi-VN")} ₫`;
        // Nội dung chuyển khoản hiển thị ở đây lấy đúng Mã phiếu (description gửi cho
        // payOS lúc tạo link) - payOS/ngân hàng có thể tự thêm tiền tố riêng vào nội dung
        // chuyển khoản THẬT, khách vẫn nên ưu tiên nội dung hiển thị trên trang/QR thanh
        // toán thật nếu có sai khác (xem models/course_registration.py
        // _create_payment_transaction).
        modalEl.querySelector("#wizard_payment_code").value = this._state.code || "";

        modalEl.querySelector("#wizard_email_sent_note").textContent =
            `Đã gửi email xác nhận kèm link phiếu đăng ký tới ${email}.`;
        modalEl.querySelector("#wizard_open_bank").href = this._state.checkoutUrl || "#";
        const pending = Boolean(this._state.pendingConfirmation);
        // Không phải cổng nào cũng có QR (VD cổng giả lập dev, vtt_payment_dev_switch) -
        // ẩn hẳn khối QR thay vì gán src="" (browser coi <img src=""> là tải lại chính
        // trang HTML hiện tại làm ảnh -> luôn ra ảnh vỡ).
        const qrImg = modalEl.querySelector("#wizard_payment_qr");
        const qrWrap = modalEl.querySelector("#wizard_payment_qr_wrap");
        qrWrap.classList.toggle("d-none", !this._state.qrUrl || pending);
        if (this._state.qrUrl) {
            qrImg.src = this._state.qrUrl;
        }
        // Có QR (payOS thật) -> khách quét QR là đủ, ẩn nút "Mở trang thanh toán" (đỡ
        // rối/trùng lặp). Không có QR (cổng giả lập dev) -> đây là cách DUY NHẤT để vào
        // được trang thanh toán, phải hiện. Diện cần xác nhận giấy tờ (pending) - CHƯA
        // có link nào cả (checkoutUrl cũng rỗng) - ẩn nút, hiện thông báo chờ xác nhận
        // thay vào đó (xem course_register_wizard.xml).
        modalEl.querySelector("#wizard_open_bank").classList.toggle(
            "d-none", Boolean(this._state.qrUrl) || pending);
        modalEl.querySelector("#wizard_payment_pending_confirmation_note").classList.toggle(
            "d-none", !pending);
        this._showPane(modalEl, "payment");

        this._startPolling();
    },

    // --- Tab 2: Thanh toán ---
    // Không còn xử lý click "mở trang ngân hàng" ở đây - nút chỉ là 1 <a target="_blank">
    // trỏ thẳng checkoutUrl, trình duyệt tự mở tab mới. Việc phát hiện thanh toán xong
    // hoàn toàn dựa vào _startPolling()/_onPaymentConfirmed() bên dưới.
    _onWizardPaymentContinue(ev) {
        const modalEl = ev.currentTarget.closest(".modal");
        this._showPane(modalEl, "detail");
    },

    _startPolling() {
        this._clearPollTimer();

        this._pollTimer = setInterval(async () => {
            if (!this._state.registrationId || this._state.paid) {
                return;
            }

            let result;
            try {
                result = await rpc("/seroto/course-registration/status", {
                    id: this._state.registrationId,
                    token: this._state.accessToken,
                });
            } catch (error) {
                console.error("Kiểm tra trạng thái thanh toán thất bại:", error);
                return;
            }

            if (result.payment_status === "paid") {
                this._state.paid = true;
                this._clearPollTimer();
                this._onPaymentConfirmed();
            }
        }, POLL_INTERVAL_MS);
    },

    _clearPollTimer() {
        if (this._pollTimer) {
            clearInterval(this._pollTimer);
            this._pollTimer = null;
        }
    },

    _onPaymentConfirmed() {
        const wizardEl = this.el.querySelector("#courseRegisterWizardModal");
        if (wizardEl) {
            wizardEl.querySelector("#wizard_payment_pending").classList.add("d-none");
            wizardEl.querySelector("#wizard_payment_success").classList.remove("d-none");
            wizardEl.querySelector('.course_wizard_step[data-step="detail"]').disabled = false;
        }
        this._syncSlip();
    },

    _onOpenSlipFromWizard(ev) {
        const wizardEl = ev.currentTarget.closest(".modal");
        this._syncSlip();
        $(wizardEl).one("hidden.bs.modal", () => this._openSlip());
        $(wizardEl).modal("hide");
    },

    // --- Tab 3: Thông tin chuyên sâu ---
    // Danh sách câu hỏi (this._state.questions) đến từ RPC create ở Tab 1 - riêng theo
    // từng khóa học (xem seroto.course.registration._get_course_questions(), khớp theo
    // TÊN khóa học với academic.course.question_ids, module seroto_education). Mỗi câu
    // hỏi có question_type ("text"/"select"/"radio") + options (mảng lựa chọn, rỗng với
    // "text") - dựng đúng loại input tương ứng. "select" và "radio" đều CHỈ chọn được 1
    // đáp án (khác nhau ở giao diện: dropdown thu gọn / các ô rời loại trừ nhau).
    _renderQuestions(modalEl) {
        const container = modalEl.querySelector("#course_wizard_questions_container");
        container.replaceChildren();

        if (!this._state.questions.length) {
            const empty = document.createElement("p");
            empty.className = "text-muted small mb-3";
            empty.textContent = "Khóa học này chưa có câu hỏi bổ sung.";
            container.appendChild(empty);
            return;
        }

        this._state.questions.forEach((q) => {
            const wrap = document.createElement("div");
            wrap.className = "mb-3";
            wrap.dataset.question = q.question;
            wrap.dataset.questionType = q.question_type;

            const label = document.createElement("label");
            label.textContent = q.question;
            wrap.appendChild(label);

            if (q.question_type === "select") {
                const select = document.createElement("select");
                select.className = "form-control course_wizard_question_input";

                const placeholder = document.createElement("option");
                placeholder.value = "";
                placeholder.textContent = "-- Chọn --";
                select.appendChild(placeholder);

                q.options.forEach((opt) => {
                    const option = document.createElement("option");
                    option.value = opt;
                    option.textContent = opt;
                    select.appendChild(option);
                });
                wrap.appendChild(select);
            } else if (q.question_type === "radio") {
                // Cùng "name" -> trình duyệt tự loại trừ nhau (chọn ô này bỏ chọn ô kia),
                // đúng ngữ nghĩa "chỉ 1 đáp án" dù giao diện trông giống nhóm checkbox rời.
                const groupName = `wizard_question_${q.id}`;
                q.options.forEach((opt, idx) => {
                    const radioWrap = document.createElement("div");
                    radioWrap.className = "form-check";

                    const radio = document.createElement("input");
                    radio.type = "radio";
                    radio.name = groupName;
                    radio.className = "form-check-input course_wizard_question_radio";
                    radio.value = opt;
                    radio.id = `${groupName}_${idx}`;

                    const radioLabel = document.createElement("label");
                    radioLabel.className = "form-check-label";
                    radioLabel.setAttribute("for", radio.id);
                    radioLabel.textContent = opt;

                    radioWrap.appendChild(radio);
                    radioWrap.appendChild(radioLabel);
                    wrap.appendChild(radioWrap);
                });
            } else {
                const input = document.createElement("input");
                input.type = "text";
                input.className = "form-control course_wizard_question_input";
                wrap.appendChild(input);
            }

            container.appendChild(wrap);
        });
    },

    async _onDetailSubmit(ev) {
        ev.preventDefault();

        const modalEl = ev.currentTarget.closest(".modal");
        const wraps = modalEl.querySelectorAll("#course_wizard_questions_container [data-question]");
        const answers = Array.from(wraps).map((wrap) => {
            let answer = "";
            if (wrap.dataset.questionType === "radio") {
                const checked = wrap.querySelector(".course_wizard_question_radio:checked");
                answer = checked ? checked.value : "";
            } else {
                const input = wrap.querySelector(".course_wizard_question_input");
                answer = input ? input.value.trim() : "";
            }
            return { question: wrap.dataset.question, answer };
        });

        try {
            await rpc("/seroto/course-registration/update", {
                id: this._state.registrationId,
                token: this._state.accessToken,
                answers,
            });
        } catch (error) {
            console.error("Lưu thông tin chuyên sâu thất bại:", error);
            alert("Có lỗi xảy ra, vui lòng thử lại.");
            return;
        }

        this._state.answers = answers;
        this._syncSlip();

        // Hoàn tất -> đóng wizard, mở lại "Phiếu đăng ký" để khách xem tóm tắt (đã
        // thanh toán nên phiếu chỉ hiện thông tin, không hiện lại khung Thanh toán).
        $(modalEl).one("hidden.bs.modal", () => this._openSlip());
        $(modalEl).modal("hide");
    },

    // --- Phiếu đăng ký khóa học (modal) ---
    _syncSlip() {
        const slipEl = this.el.querySelector("#courseRegistrationSlipModal");
        if (!slipEl) {
            return;
        }

        slipEl.querySelector("#slip_course").textContent = this._state.course;
        slipEl.querySelector("#slip_name").textContent = this._state.name;
        slipEl.querySelector("#slip_email").textContent = this._state.email;
        slipEl.querySelector("#slip_phone").textContent = this._state.phone;

        // Chỉ hiện dòng "Học viên" khi đăng ký hộ người khác - đăng ký cho bản thân thì
        // Người đăng ký ở trên đã chính là học viên, hiện thêm dòng này sẽ thừa/gây rối.
        const studentRowEl = slipEl.querySelector("#slip_student_row");
        const isForOther = this._state.studentRelation === "other";
        studentRowEl.classList.toggle("d-none", !isForOther);
        if (isForOther) {
            slipEl.querySelector("#slip_student").textContent = this._state.studentName;
        }

        const answersEl = slipEl.querySelector("#slip_answers");
        answersEl.replaceChildren();
        this._state.answers.forEach((a) => {
            const p = document.createElement("p");
            p.className = "mb-1";
            p.textContent = `${a.question}: ${a.answer || "-"}`;
            answersEl.appendChild(p);
        });

        const statusEl = slipEl.querySelector("#slip_payment_status");
        const paymentSection = slipEl.querySelector("#slip_payment_section");

        if (this._state.paid) {
            statusEl.textContent = "Đã thanh toán";
            statusEl.className = "badge text-bg-success";
            paymentSection.classList.add("d-none");
        } else {
            statusEl.textContent = "Chưa thanh toán";
            statusEl.className = "badge text-bg-danger";
            paymentSection.classList.remove("d-none");
            const openBankLink = slipEl.querySelector("#slip_open_bank");
            if (openBankLink) {
                openBankLink.href = this._state.checkoutUrl || "#";
            }
            const qrImg = slipEl.querySelector("#slip_payment_qr");
            if (qrImg && this._state.qrUrl) {
                qrImg.src = this._state.qrUrl;
            }
        }
    },

    _openSlip() {
        this._syncSlip();
        $(this.el.querySelector("#courseRegistrationSlipModal")).modal("show");
        if (!this._state.paid) {
            this._startPolling();
        }
    },

    // --- Trang xem phiếu qua link email (views/course_registration_slip_page.xml) ---
    // Trang tĩnh (server-render), không có nút tự khai thanh toán nữa - chỉ polling rồi
    // tải lại trang khi phát hiện đã thanh toán để hiện đúng bản server-render mới.
    _pollSlipPage(root) {
        const { registrationId, registrationToken } = root.dataset;

        this._slipPagePollTimer = setInterval(async () => {
            let result;
            try {
                result = await rpc("/seroto/course-registration/status", {
                    id: registrationId,
                    token: registrationToken,
                });
            } catch (error) {
                console.error("Kiểm tra trạng thái thanh toán thất bại:", error);
                return;
            }

            if (result.payment_status === "paid") {
                clearInterval(this._slipPagePollTimer);
                window.location.reload();
            }
        }, POLL_INTERVAL_MS);
    },

    // --- Câu hỏi chuyên sâu CHƯA trả lời trên trang xem phiếu (link email) ---
    // Route /seroto/course-registration/update GHI ĐÈ TOÀN BỘ answer_ids mỗi lần gọi
    // (xem controllers/course_registration.py) - phải gộp câu trả lời cũ (data-existing-
    // answers, server tính sẵn) với câu mới điền ở đây rồi gửi CẢ HAI, nếu không sẽ mất
    // answer đã lưu trước đó.
    async _onSlipQuestionsSubmit(ev) {
        ev.preventDefault();

        const form = ev.currentTarget;
        const root = this.el.querySelector("#course_registration_slip_page_root");
        const { registrationId, registrationToken, existingAnswers } = root.dataset;

        const wraps = form.querySelectorAll("[data-question]");
        const newAnswers = Array.from(wraps).map((wrap) => {
            let answer = "";
            if (wrap.dataset.questionType === "radio") {
                const checked = wrap.querySelector(".slip_question_radio:checked");
                answer = checked ? checked.value : "";
            } else {
                const input = wrap.querySelector(".slip_question_input");
                answer = input ? input.value.trim() : "";
            }
            return { question: wrap.dataset.question, answer };
        });

        const submitBtn = form.querySelector("button[type='submit']");
        submitBtn.disabled = true;

        try {
            await rpc("/seroto/course-registration/update", {
                id: registrationId,
                token: registrationToken,
                answers: JSON.parse(existingAnswers || "[]").concat(newAnswers),
            });
        } catch (error) {
            console.error("Lưu câu trả lời thất bại:", error);
            alert("Có lỗi xảy ra, vui lòng thử lại.");
            submitBtn.disabled = false;
            return;
        }

        window.location.reload();
    },

    // --- Dùng chung cho cả wizard: đổi bước đang active + hiện đúng pane ---
    _showPane(modalEl, step) {
        modalEl.querySelectorAll(".course_wizard_step").forEach((btn) => {
            btn.classList.toggle("active", btn.dataset.step === step);
        });
        modalEl.querySelectorAll(".course_wizard_pane").forEach((pane) => {
            pane.classList.toggle("d-none", pane.dataset.pane !== step);
        });
    },

});
