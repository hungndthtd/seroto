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
            // [{id, question, question_type, options, is_shared, category_codes}, ...] -
            // CHƯA lọc theo diện (server trả nguyên cả bộ), tự lọc lại theo diện đang
            // chọn mỗi khi render - xem _renderBasicQuestions.
            basicQuestions: [],
            // [{code, name, requires_review, requires_upload, template_url}, ...] - CHỈ
            // những diện đang website_visible=True cho ĐÚNG khóa học này (xem controllers/
            // academic_course_snippet.py, academic_course_is_registration_open) - nguồn
            // duy nhất để dựng <option> của #wizard_registration_category, biết diện
            // đang chọn có yêu cầu upload hay không, VÀ link tải mẫu giấy tờ (xem
            // _renderRegistrationCategoryOptions, _onCategoryChange, _onBasicSubmit) -
            // không còn hardcode "5 diện cố định"/UPLOAD_CATEGORIES như trước.
            registrationCategories: [],
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
            this._showNotice(`Khóa học "${course}" hiện chưa mở đăng ký, vui lòng quay lại sau hoặc liên hệ Seroto để được tư vấn.`);
            return;
        }

        this._clearPollTimer();

        this._state = this._emptyState();
        this._state.course = course;
        this._state.basicQuestions = openCheck.basic_questions || [];
        this._state.registrationCategories = openCheck.registration_categories || [];

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
        // Diện đăng ký - danh sách <option> giờ DỰNG LẠI TỪ ĐẦU mỗi lần mở modal, CHỈ
        // gồm đúng những diện đang active=True cho khóa học này (xem
        // _renderRegistrationCategoryOptions) - không còn cố định "tuition" làm mặc định
        // như trước (khóa có thể tắt hẳn diện tuition). Gọi lại _onCategoryChange ngay
        // sau đó (y hệt lúc khách tự đổi dropdown) để ẩn/hiện + bật/tắt required đúng
        // theo diện ĐẦU TIÊN thực tế đang được chọn, thay vì tự giả định "tuition".
        this._renderRegistrationCategoryOptions(modalEl);
        // Khóa chưa cấu hình website_visible=True cho diện nào (mặc định giờ là False,
        // xem academic.course.pricing.website_visible) -> registrationCategories rỗng ->
        // ẩn hẳn khối "Diện đăng ký" thay vì hiện dropdown rỗng không chọn được gì. Select
        // vốn không có required="required" (xem course_register_wizard.xml) nên ẩn khối
        // này KHÔNG chặn nút "Tiếp tục" nếu Thông tin cơ bản đã điền đủ.
        modalEl.querySelector("#wizard_registration_category_section").classList.toggle(
            "d-none", this._state.registrationCategories.length === 0);
        modalEl.querySelector("#wizard_category_attachment_input").value = "";
        this._onCategoryChange({ currentTarget: modalEl.querySelector("#wizard_registration_category") });
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

    // Dựng lại <option> của #wizard_registration_category từ this._state.registrationCategories
    // (đã lọc theo ĐÚNG khóa học + active=True, xem _onOpenWizard) - chọn sẵn diện ĐẦU
    // TIÊN trong danh sách (sequence nhỏ nhất, thứ tự server đã trả đúng - xem
    // academic.course.pricing._order). Khóa không cấu hình diện nào cả (danh sách rỗng,
    // lẽ ra không nên xảy ra vì academic.course.create() tự sinh đủ dòng) thì để
    // <select> rỗng - form vẫn gửi registration_category="" lên server, server tự chặn
    // lại (không có diện nào khớp).
    _renderRegistrationCategoryOptions(modalEl) {
        const select = modalEl.querySelector("#wizard_registration_category");
        select.replaceChildren();
        this._state.registrationCategories.forEach((cat, idx) => {
            const option = document.createElement("option");
            option.value = cat.code;
            option.textContent = cat.name;
            if (idx === 0) {
                option.selected = true;
            }
            select.appendChild(option);
        });
    },

    // "Diện đăng ký": hiện đúng (các) khối field theo diện đã chọn - medical/nonprofit
    // hiện CẢ khối riêng LẪN khối "upload" dùng chung (diện cần nộp giấy tờ). Đúng
    // pattern _onRelationChange, chỉ áp dụng cho nhiều khối hơn 1.
    _onCategoryChange(ev) {
        const modalEl = ev.currentTarget.closest(".modal");
        const category = ev.currentTarget.value;

        // Cấu trúc field RIÊNG của từng diện (voucher/medical/nonprofit có field đặc thù
        // không diện nào khác dùng chung) - vẫn hardcode ở đây, cố tình KHÔNG đưa vào
        // academic.registration.category (danh mục đó chỉ nắm 2 quyết định NGHIỆP VỤ
        // dùng chung là requires_review/requires_upload, không nắm cấu trúc FORM). Diện
        // đóng học phí không có khối riêng nào trên website (xem
        // views/course_register_wizard.xml) - "Trạng thái đăng ký" chỉ nhân viên tự
        // chọn tay trên backend.
        const STRUCTURAL_BLOCKS_BY_CATEGORY = {
            tuition: [],
            voucher: ["voucher"],
            education_scholarship: [],
            medical_scholarship: ["medical"],
            nonprofit: ["nonprofit"],
        };
        // Khối "upload" dùng chung - hiện hay không giờ đọc THẲNG từ requires_upload của
        // đúng diện đang chọn (this._state.registrationCategories, nguồn từ
        // academic.registration.category) thay vì mảng UPLOAD_CATEGORIES hardcode cố
        // định như trước - đổi cấu hình ở màn "Loại diện đăng ký" (backend) là form tự
        // theo, không cần sửa code.
        const categoryInfo = this._state.registrationCategories.find((c) => c.code === category);
        const requiresUpload = Boolean(categoryInfo && categoryInfo.requires_upload);
        const visibleBlocks = STRUCTURAL_BLOCKS_BY_CATEGORY[category] || [];
        if (requiresUpload) {
            visibleBlocks.push("upload");
        }

        // required="required" TĨNH trong HTML KHÔNG đủ - đã kiểm chứng thực tế (Chrome
        // DevTools, reportValidity()): input nằm trong khối display:none (d-none) VẪN bị
        // tính "invalid" và chặn checkValidity() của CẢ FORM (chỉ là trình duyệt không
        // focus/hiện popup được vào đó nên im lặng chặn, dễ tưởng nhầm nút bị "kẹt") -
        // PHẢI tự bật/tắt .required bằng JS đúng lúc ẩn/hiện khối, không phó mặc cho
        // trình duyệt tự loại trừ như vẫn tưởng trước đây. "voucher" NẰM trong danh sách
        // này (đổi lại - trước đây "Mã voucher" không bắt buộc, gây lỗi thực tế: khách
        // chọn diện voucher, để trống mã, vẫn bấm "Tiếp tục" được và đăng ký với GIÁ ĐẦY
        // ĐỦ không có ưu đãi nào - xem thêm chặn phía server ở _prepare_registration_vals,
        // module vtt_seroto_website/controllers/course_registration.py).
        const REQUIRED_BLOCKS = ["upload", "medical", "nonprofit", "voucher"];
        ["voucher", "upload", "medical", "nonprofit"].forEach((name) => {
            const blockEl = modalEl.querySelector(`#wizard_category_${name}_fields`);
            const isVisible = visibleBlocks.includes(name);
            blockEl.classList.toggle("d-none", !isVisible);
            if (REQUIRED_BLOCKS.includes(name)) {
                blockEl.querySelectorAll("input, select").forEach((input) => {
                    input.required = isVisible;
                });
            }
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
        // Link tải mẫu - đọc THẲNG từ template_url của đúng diện đang chọn
        // (this._state.registrationCategories, nguồn academic.registration.category) thay
        // vì chỉ ẩn/hiện cứng theo 2 mã diện hardcode như trước - diện nào Quản lý chưa
        // nhập link (để trống) thì KHÔNG hiện link, không phân biệt CODE diện là gì.
        const templateUrl = (categoryInfo && categoryInfo.template_url) || "";
        const templateLinkEl = modalEl.querySelector("#wizard_category_template_link");
        templateLinkEl.classList.toggle("d-none", !templateUrl);
        templateLinkEl.href = templateUrl || "#";

        // "Câu hỏi cơ bản" áp dụng theo diện có thể khác hẳn diện vừa đổi - render lại
        // TOÀN BỘ (mất câu trả lời cũ nếu có), cùng tinh thần "đổi diện thì xóa giá trị
        // field của diện không còn liên quan" đã áp dụng cho các khối trên.
        this._renderBasicQuestions(modalEl);

        this._updateBasicContinueState(modalEl);
    },

    // "Câu hỏi cơ bản" (Bước 1) - lọc this._state.basicQuestions (CHƯA lọc, server trả
    // nguyên cả bộ lúc mở modal) theo ĐÚNG diện đang chọn (is_shared hoặc khớp
    // category_codes), render input y hệt _renderQuestions() (Tab 3) nhưng CÓ
    // required="required" (select/text bắt cả nhóm, radio bắt TỪNG ô trong nhóm) - khác
    // Tab 3 (không bắt buộc trả lời trước khi "Hoàn tất đăng ký").
    _renderBasicQuestions(modalEl) {
        const container = modalEl.querySelector("#wizard_basic_questions_container");

        // Giữ lại câu trả lời/tick ĐÃ có TRƯỚC khi xóa - hàm này bị gọi lại MỖI LẦN đổi
        // "Diện đăng ký" (kể cả câu "Dùng chung", is_shared=True, hoàn toàn không phụ
        // thuộc diện) - không giữ lại thì khách tick xong đổi diện là mất tick, tưởng
        // nút "Tiếp tục" bị kẹt dù thực ra chỉ là mất dữ liệu đã nhập.
        const existingAnswers = {};
        container.querySelectorAll("[data-question]").forEach((wrap) => {
            if (wrap.dataset.questionType === "radio") {
                const checked = wrap.querySelector(".course_wizard_basic_question_radio:checked");
                if (checked) existingAnswers[wrap.dataset.question] = checked.value;
            } else if (wrap.dataset.questionType === "checkbox") {
                const checkbox = wrap.querySelector(".course_wizard_basic_question_checkbox");
                existingAnswers[wrap.dataset.question] = Boolean(checkbox && checkbox.checked);
            } else {
                const input = wrap.querySelector(".course_wizard_basic_question_input");
                if (input) existingAnswers[wrap.dataset.question] = input.value;
            }
        });

        container.replaceChildren();

        const category = modalEl.querySelector("#wizard_registration_category").value;
        const questions = this._state.basicQuestions.filter(
            (q) => q.is_shared || q.category_codes.includes(category),
        );

        questions.forEach((q) => {
            const wrap = document.createElement("div");
            wrap.className = "mb-3";
            wrap.dataset.question = q.question;
            wrap.dataset.questionType = q.question_type;

            // "checkbox" KHÔNG hiện nhãn riêng phía trên - chính câu hỏi (q.question)
            // đóng vai trò nhãn của ô tích, y hệt bố cục checkbox "Tôi cam kết thông
            // tin đăng ký..." hard-code sẵn trên form (form-check: input + label cùng
            // hàng) - hiện nhãn riêng ở đây sẽ bị lặp lại nội dung 2 lần.
            if (q.question_type !== "checkbox") {
                const label = document.createElement("label");
                label.textContent = q.question;
                wrap.appendChild(label);
            }

            if (q.question_type === "checkbox") {
                const checkWrap = document.createElement("div");
                checkWrap.className = "form-check";

                const checkbox = document.createElement("input");
                checkbox.type = "checkbox";
                checkbox.className = "form-check-input course_wizard_basic_question_checkbox";
                checkbox.id = `wizard_basic_question_${q.id}`;
                checkbox.required = true;
                checkbox.checked = Boolean(existingAnswers[q.question]);

                const checkLabel = document.createElement("label");
                checkLabel.className = "form-check-label";
                checkLabel.setAttribute("for", checkbox.id);
                checkLabel.textContent = q.question;

                checkWrap.appendChild(checkbox);
                checkWrap.appendChild(checkLabel);
                wrap.appendChild(checkWrap);
            } else if (q.question_type === "select") {
                const select = document.createElement("select");
                select.className = "form-control course_wizard_basic_question_input";
                select.required = true;

                // KHÔNG thêm option rỗng "-- Chọn --" - mặc định trình duyệt tự chọn
                // SẴN lựa chọn ĐẦU TIÊN khai trên Khóa học (khác Tab 3 "Câu hỏi chuyên
                // sâu", _renderQuestions() vẫn giữ placeholder rỗng - nơi đó cần phân
                // biệt "đã trả lời"/"chưa trả lời" để hiện lại đúng câu còn thiếu, có
                // sẵn mặc định sẽ luôn coi là "đã trả lời" ngay từ đầu).
                q.options.forEach((opt) => {
                    const option = document.createElement("option");
                    option.value = opt;
                    option.textContent = opt;
                    select.appendChild(option);
                });
                if (q.options.includes(existingAnswers[q.question])) {
                    select.value = existingAnswers[q.question];
                }
                wrap.appendChild(select);
            } else if (q.question_type === "radio") {
                const groupName = `wizard_basic_question_${q.id}`;
                q.options.forEach((opt, idx) => {
                    const radioWrap = document.createElement("div");
                    radioWrap.className = "form-check";

                    const radio = document.createElement("input");
                    radio.type = "radio";
                    radio.name = groupName;
                    radio.className = "form-check-input course_wizard_basic_question_radio";
                    radio.value = opt;
                    radio.id = `${groupName}_${idx}`;
                    radio.required = true;
                    radio.checked = existingAnswers[q.question] === opt;

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
                input.className = "form-control course_wizard_basic_question_input";
                input.required = true;
                input.value = existingAnswers[q.question] || "";
                wrap.appendChild(input);
            }

            container.appendChild(wrap);
        });
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

        // Diện có requires_upload=True dùng CHUNG 1 ô chọn file - đọc + encode base64
        // TRƯỚC khi khóa nút "Tiếp tục" (route hiện tại là jsonrpc thuần, không phải
        // multipart, nên phải gửi file dạng base64 kèm trong payload JSON). Đọc thẳng từ
        // this._state.registrationCategories (nguồn academic.registration.category) thay
        // vì mảng hardcode cố định như trước.
        let attachments = [];
        const submitCategoryInfo = this._state.registrationCategories.find((c) => c.code === category);
        if (submitCategoryInfo && submitCategoryInfo.requires_upload) {
            const MAX_SIZE = 10 * 1024 * 1024;
            const files = Array.from(modalEl.querySelector("#wizard_category_attachment_input").files || []);
            const tooLarge = files.find((file) => file.size > MAX_SIZE);
            if (tooLarge) {
                this._showNotice(`File "${tooLarge.name}" vượt quá 10MB, vui lòng chọn file khác.`);
                return;
            }
            try {
                attachments = await Promise.all(files.map((file) => this._fileToAttachment(file)));
            } catch (error) {
                console.error("Đọc file đính kèm thất bại:", error);
                this._showNotice("Không đọc được file đính kèm, vui lòng thử lại.");
                return;
            }
        }

        // "Câu hỏi cơ bản" - thu thập TỪ ĐÚNG các input đang render trong container (đã
        // lọc theo diện, xem _renderBasicQuestions) - cùng cách đọc radio/select/text như
        // _onDetailSubmit (Tab 3), nhưng gửi kèm NGAY trong payload Tab 1 (khác Tab 3, gửi
        // qua route /update riêng SAU KHI phiếu đã tồn tại).
        const basicWraps = modalEl.querySelectorAll("#wizard_basic_questions_container [data-question]");
        const basicAnswers = Array.from(basicWraps).map((wrap) => {
            let answer = "";
            if (wrap.dataset.questionType === "radio") {
                const checked = wrap.querySelector(".course_wizard_basic_question_radio:checked");
                answer = checked ? checked.value : "";
            } else if (wrap.dataset.questionType === "checkbox") {
                // Lưu nhãn dễ đọc cho NV xem trên backend, thay vì "yes" khô khan - rỗng
                // nếu chưa tích (không nên xảy ra vì input required, chỉ phòng hờ).
                const checkbox = wrap.querySelector(".course_wizard_basic_question_checkbox");
                answer = checkbox && checkbox.checked ? "Xác nhận/Đồng ý" : "";
            } else {
                const input = wrap.querySelector(".course_wizard_basic_question_input");
                answer = input ? input.value.trim() : "";
            }
            return { question: wrap.dataset.question, answer };
        });

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
            registration_category: category,
            attachments,
            basic_answers: basicAnswers,
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
            this._showNotice(serverMessage || "Có lỗi xảy ra, vui lòng thử lại.");
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
            this._showNotice("Có lỗi xảy ra, vui lòng thử lại.");
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
            this._showNotice("Có lỗi xảy ra, vui lòng thử lại.");
            submitBtn.disabled = false;
            return;
        }

        window.location.reload();
    },

    // --- Dùng CHUNG cho cả wizard: hiện thông báo lỗi/thông tin qua modal riêng
    // (#courseWizardNoticeModal, views/course_register_wizard.xml) thay vì alert() mặc
    // định của trình duyệt (giao diện xấu, không đồng bộ) - GỌI ĐƯỢC ở mọi lúc, kể cả
    // TRƯỚC KHI modal wizard mở (VD "Khóa học chưa mở đăng ký" ở _onOpenWizard) hay
    // trong lúc modal wizard ĐANG mở (VD "Mã voucher không hợp lệ" ở _onBasicSubmit) -
    // Bootstrap tự xếp đúng z-index/backdrop khi 2 modal chồng nhau. ---
    _showNotice(message, title) {
        const noticeEl = this.el.querySelector("#courseWizardNoticeModal");
        if (!noticeEl) {
            // Phòng hờ template chưa kịp render (không nên xảy ra thực tế) - fallback về
            // alert() gốc để KHÔNG BAO GIỜ nuốt mất thông báo lỗi.
            window.alert(message);
            return;
        }
        noticeEl.querySelector("#courseWizardNoticeModalLabel").textContent = title || "Thông báo";
        noticeEl.querySelector("#wizard_notice_message").textContent = message;
        $(noticeEl).modal("show");
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
