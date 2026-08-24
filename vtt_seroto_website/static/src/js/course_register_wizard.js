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
        "change input[name='student_relation']": "_onRelationChange",
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
    _onOpenWizard(ev) {
        ev.preventDefault();
        this._clearPollTimer();

        this._state = this._emptyState();
        this._state.course = ev.currentTarget.dataset.course || "";

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

        const continueBtn = modalEl.querySelector("#wizard_basic_continue");
        continueBtn.disabled = true;
        continueBtn.textContent = "Đang xử lý...";

        let result;
        try {
            result = await rpc("/seroto/course-registration/create", {
                course: this._state.course,
                name,
                email,
                phone,
                student_relation: studentRelation,
                student_name: studentName,
            });
        } catch (error) {
            console.error("Tạo phiếu đăng ký thất bại:", error);
            alert("Có lỗi xảy ra, vui lòng thử lại.");
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

        this._renderQuestions(modalEl);

        continueBtn.textContent = "Tiếp tục";
        continueBtn.disabled = false;

        // Lưu vào "Phiếu đăng ký khóa học" (modal khác) rồi chuyển wizard sang tab
        // Thanh toán - đúng theo yêu cầu luồng.
        this._syncSlip();

        modalEl.querySelector('.course_wizard_step[data-step="payment"]').disabled = false;
        modalEl.querySelector("#wizard_payment_course").textContent = this._state.course;

        // Hiện đầy đủ lại thông tin đã điền ở Tab 1 (giống hệt phần "Phiếu đăng ký" ở
        // _syncSlip) để khách đối chiếu lại trước khi thanh toán - không còn dòng "Nội
        // dung chuyển khoản" tự đoán như trước (payOS/ngân hàng có thể tự thêm tiền tố
        // riêng vào nội dung chuyển khoản thật, hiện sai còn dễ gây nhầm lẫn hơn không
        // hiện - khách xem đúng nội dung thật ngay trên trang/QR của payOS).
        const isForOther = this._state.studentRelation === "other";
        modalEl.querySelector("#wizard_payment_student_row").classList.toggle("d-none", !isForOther);
        if (isForOther) {
            modalEl.querySelector("#wizard_payment_student").textContent = this._state.studentName;
        }
        modalEl.querySelector("#wizard_payment_name").textContent = this._state.name;
        modalEl.querySelector("#wizard_payment_email").textContent = this._state.email;
        modalEl.querySelector("#wizard_payment_phone").textContent = this._state.phone;

        modalEl.querySelector("#wizard_email_sent_note").textContent =
            `Đã gửi email xác nhận kèm link phiếu đăng ký tới ${email}.`;
        modalEl.querySelector("#wizard_open_bank").href = this._state.checkoutUrl || "#";
        modalEl.querySelector("#wizard_payment_qr").src = this._state.qrUrl || "";
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
