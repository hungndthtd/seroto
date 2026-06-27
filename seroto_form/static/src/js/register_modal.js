/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.CourseRegister = publicWidget.Widget.extend({

    selector: "#wrap",

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

        // Reset button
        $("#submit_btn")
            .prop("disabled", false)
            .html("Đăng ký");

        // Show modal
        $("#courseRegisterModal").modal("show");
    },

    _onSubmit() {

        $("#submit_btn")
            .prop("disabled", true)
            .html(
                '<span class="spinner-border spinner-border-sm me-2"></span>Đang gửi...'
            );
    },

});