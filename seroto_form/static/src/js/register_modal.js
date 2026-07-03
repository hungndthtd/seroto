/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.CourseRegister = publicWidget.Widget.extend({

    // "#wrapwrap" (không phải "#wrap"): modal đăng ký được gắn vào website.layout, làm
    // con của #wrapwrap (xem views/course_register_modal.xml) để tránh CSRF token bị
    // đóng băng khi lưu trang - nghĩa là form #course_register_form nằm ngoài #wrap
    // nhưng vẫn trong #wrapwrap. LƯU Ý: cơ chế gắn public widget của Odoo mặc định chỉ
    // tìm kiếm bên trong #wrapwrap - dùng "body" ở đây sẽ khiến widget KHÔNG BAO GIỜ
    // được gắn (không lỗi, chỉ im lặng không chạy).
    selector: "#wrapwrap",

    events: {
        "click .register-course": "_onRegisterClick",
        "submit #course_register_form": "_onSubmit",
    },

    start() {
        console.log("Course Register Widget Started");
        return this._super(...arguments);
    },

    _onRegisterClick(ev) {

        ev.preventDefault();

        const course = ev.currentTarget.dataset.course;
        const price = ev.currentTarget.dataset.price;

        console.log("Selected Course:", course);

        // Reset form
        const form = document.getElementById("course_register_form");

        if (form) {
            form.reset();
        }

        // Hiển thị tên khóa học
        $("#course_name").val(course);

        // Giá trị submit
        $("#course_value").val(course);

        // Giá khóa học
        $("#course_price").val(price);

        // Reset button
        $("#submit_btn")
            .prop("disabled", false)
            .html("Đăng ký");

        // Show modal
        $("#courseRegisterModal").modal("show");
    },

    _onSubmit(ev) {

        // Submit bằng AJAX (không reload trang) để có thể hiển thị modal
        // "Đăng ký thành công" ngay sau khi server xử lý xong.
        ev.preventDefault();

        const form = ev.currentTarget;
        const params = Object.fromEntries(new FormData(form).entries());

        $("#submit_btn")
            .prop("disabled", true)
            .html(
                '<span class="spinner-border spinner-border-sm me-2"></span>Đang gửi...'
            );

        rpc("/course/register", params)
            .then((result) => {
                $("#submit_btn").prop("disabled", false).html("Đăng ký");

                // Đợi modal đăng ký đóng hẳn rồi mới mở modal thành công, tránh
                // 2 backdrop chồng nhau.
                $("#courseRegisterModal").one("hidden.bs.modal", () => {
                    if (result && result.course) {
                        this._showSuccessModal(result.course);
                    }
                });
                $("#courseRegisterModal").modal("hide");
            })
            .catch((error) => {
                console.error("Course register failed:", error);
                $("#submit_btn").prop("disabled", false).html("Đăng ký");
                alert("Đăng ký không thành công, vui lòng thử lại.");
            });
    },

    _showSuccessModal(course) {

        document.getElementById("success_course_name").textContent = course.name;

        const img = document.getElementById("success_course_image");
        img.src = course.image_url;
        img.alt = course.name;

        document.getElementById("success_course_type").textContent = course.course_type_label;
        document.getElementById("success_course_teacher").textContent = course.teacher;
        document.getElementById("success_course_date").textContent = course.next_class_date || "Sắp công bố";
        document.getElementById("success_course_time").textContent = course.schedule_note || "Sắp công bố";

        $("#courseRegisterSuccessModal").modal("show");
    },

});