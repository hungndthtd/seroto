/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

// Widget này CHỈ chịu trách nhiệm nạp lại danh sách khóa học MỚI NHẤT khi trang thực sự
// tải trên frontend (tránh nội dung "đóng băng" từ lúc kéo thả/lưu snippet vào trang).
// Việc mở modal đăng ký khi bấm nút đã được xử lý sẵn bởi widget CourseRegister
// (register_modal.js, gắn trên #wrap của MỌI trang) thông qua class "register-course"
// + data-course/data-price - nên KHÔNG lặp lại logic mở modal ở đây để tránh 2 đoạn JS
// tranh nhau mở modal (đây chính là nguyên nhân snippet cũ bị lỗi).
publicWidget.registry.SerotoCourseSnippet = publicWidget.Widget.extend({

    selector: '.s_dynamic_course_card',

    start() {
        this._super(...arguments);
        this._loadCourses().catch(console.error);
        return this;
    },

    async _loadCourses() {
        // data-audience-code: gắn sẵn trên section của từng biến thể snippet
        // (vd s_dynamic_course_card_teacher) để chỉ lọc đúng khóa học của đề mục đó.
        // Không có thì lấy danh sách chung (snippet "Khóa học nổi bật").
        const audienceCode = this.el.dataset.audienceCode || null;
        const courses = await rpc("/seroto/course/list", { audience_code: audienceCode });
        this._renderCourses(courses);
    },

    _renderCourses(courses) {
        const container = this.el.querySelector('.js_course_container');

        if (!container) {
            console.warn("Seroto: .js_course_container not found");
            return;
        }

        container.innerHTML = '';

        // Dựng DOM bằng createElement/textContent (không dùng innerHTML nối chuỗi)
        // để tránh XSS nếu tên/mô tả khóa học chứa ký tự HTML đặc biệt.
        courses.forEach((course) => {
            const col = document.createElement('div');
            col.className = 'col-lg-4 mb-4';

            const card = document.createElement('div');
            card.className = 'card h-100 shadow-sm';

            const img = document.createElement('img');
            img.className = 'card-img-top';
            img.style.height = '220px';
            img.style.objectFit = 'cover';
            img.src = course.image_url;
            img.alt = course.name;
            card.appendChild(img);

            const body = document.createElement('div');
            body.className = 'card-body';

            const title = document.createElement('h4');
            title.textContent = course.name;
            body.appendChild(title);

            const subtitle = document.createElement('p');
            subtitle.textContent = course.subtitle;
            body.appendChild(subtitle);

            const desc = document.createElement('p');
            desc.style.fontSize = '14px';
            desc.textContent = course.description;
            body.appendChild(desc);

            const teacher = document.createElement('p');
            teacher.textContent = course.teacher;
            body.appendChild(teacher);

            if (course.enrollment_label) {
                const enrollment = document.createElement('p');
                enrollment.textContent = `Tuyển sinh: ${course.enrollment_label}`;
                body.appendChild(enrollment);
            }

            // Luôn hiện 3 dòng này (kể cả khi chưa có lớp/ngày cụ thể) với placeholder
            // "Sắp công bố" - tránh card bị "thiếu" trông không đồng bộ với card khác.
            const nextClass = document.createElement('p');
            nextClass.textContent = `Ngày học: ${course.next_class_date || 'Sắp công bố'}`;
            body.appendChild(nextClass);

            const schedule = document.createElement('p');
            schedule.textContent = `Thời gian: ${course.schedule_note || 'Sắp công bố'}`;
            body.appendChild(schedule);

            const deadline = document.createElement('p');
            deadline.textContent = `Thời hạn đăng ký: ${course.registration_deadline || 'Sắp công bố'}`;
            body.appendChild(deadline);

            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn btn-primary register-course';
            btn.dataset.course = course.name;
            btn.dataset.price = course.tuition_fee;
            if (course.registration_open) {
                btn.textContent = 'Đăng ký ngay';
            } else {
                // Khóa học đang ở trạng thái "Đang chờ" (chưa mở đăng ký) - vô hiệu
                // hóa nút, không gắn class "register-course" nên click cũng không
                // mở modal đăng ký (phòng trường hợp bấm được qua devtools).
                btn.disabled = true;
                btn.classList.remove('register-course');
                btn.textContent = 'Sắp mở đăng ký';
            }
            body.appendChild(btn);

            card.appendChild(body);
            col.appendChild(card);
            container.appendChild(col);
        });
    },
});
