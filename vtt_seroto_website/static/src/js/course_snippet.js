/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

// Tạo <i class="fa {iconClass} me-1"/> - dùng lại cho các dòng icon trong card, khớp
// với views/snippets/s_course_card.xml (bản QWeb tĩnh).
function _makeIcon(iconClass) {
    const icon = document.createElement('i');
    icon.className = `fa ${iconClass} me-1`;
    return icon;
}

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

            // d-flex flex-column: cần thiết để nút mt-auto (thêm bên dưới) đẩy hàng
            // nút xuống sát đáy thẻ dù mô tả khóa học dài/ngắn khác nhau - khớp với
            // bản QWeb tĩnh (views/snippets/s_course_card.xml).
            const body = document.createElement('div');
            body.className = 'card-body d-flex flex-column';

            const title = document.createElement('h4');
            title.textContent = course.name;
            title.className = 'text-indigo';
            body.appendChild(title);

            const subtitle = document.createElement('p');
            subtitle.textContent = course.subtitle;
            body.appendChild(subtitle);

            // Badge "Hình thức học" (Online Zoom/Offline), màu theo course_type -
            // khớp với views/snippets/s_course_card.xml (bản QWeb tĩnh).
            const badgeClass = course.course_type === 'online' ? 'success' : 'danger';
            const badge = document.createElement('span');
            badge.className = `py-0.5 px-2 mb-2 d-inline-block align-self-start rounded-pill border border-${badgeClass} text-${badgeClass}`;
            badge.style.fontSize = '12px';
            badge.appendChild(_makeIcon('fa-circle'));
            badge.appendChild(document.createTextNode(course.course_type_label));
            body.appendChild(badge);

            const desc = document.createElement('p');
            desc.style.fontSize = '14px';
            desc.textContent = course.description;
            body.appendChild(desc);

            const teacher = document.createElement('p');
            teacher.appendChild(_makeIcon('fa-user'));
            teacher.appendChild(document.createTextNode(course.teacher));
            body.appendChild(teacher);

            if (course.enrollment_label) {
                const enrollment = document.createElement('p');
                enrollment.appendChild(_makeIcon('fa-info-circle'));
                enrollment.appendChild(document.createTextNode(`Tuyển sinh: ${course.enrollment_label}`));
                body.appendChild(enrollment);
            }

            // Luôn hiện 3 dòng này (kể cả khi chưa có lớp/ngày cụ thể) với placeholder
            // "Sắp công bố" - tránh card bị "thiếu" trông không đồng bộ với card khác.
            const nextClass = document.createElement('p');
            nextClass.appendChild(_makeIcon('fa-calendar'));
            nextClass.appendChild(document.createTextNode(`Ngày học: ${course.next_class_date || 'Sắp công bố'}`));
            body.appendChild(nextClass);

            const schedule = document.createElement('p');
            schedule.appendChild(_makeIcon('fa-clock-o'));
            schedule.appendChild(document.createTextNode(`Thời gian: ${course.schedule_note || 'Sắp công bố'}`));
            body.appendChild(schedule);

            const deadline = document.createElement('p');
            deadline.appendChild(_makeIcon('fa-hourglass-half'));
            deadline.appendChild(document.createTextNode(`Thời hạn đăng ký: ${course.registration_deadline || 'Sắp công bố'}`));
            body.appendChild(deadline);

            // Bọc 2 nút trong 1 hàng flex dàn đều (justify-content-between + flex-fill
            // trên từng nút) - khớp với bản QWeb tĩnh (views/snippets/s_course_card.xml).
            // mt-auto (thay vì mt-3 cố định): đẩy hàng nút xuống sát đáy thẻ dù mô tả
            // khóa học dài/ngắn khác nhau, các thẻ cùng hàng luôn thẳng hàng nút.
            const btnRow = document.createElement('div');
            btnRow.className = 'd-flex justify-content-between gap-2 mt-auto pt-3';

            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn btn-primary register-course flex-fill';
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
            btnRow.appendChild(btn);

            // Chỉ hiện khi khóa học có trang landing riêng (field
            // seroto.course.landing_page_url, nhập tay qua form Khóa học) - link thẳng,
            // khớp với nút "Chi tiết" trong bản QWeb tĩnh (views/snippets/s_course_card.xml).
            // target="_blank": mở trang khóa học ở tab mới, không mất trang đang xem.
            if (course.landing_page_url) {
                const detailLink = document.createElement('a');
                detailLink.className = 'btn btn-outline-primary flex-fill';
                detailLink.href = course.landing_page_url;
                detailLink.target = '_blank';
                detailLink.rel = 'noopener';
                detailLink.textContent = 'Chi tiết';
                btnRow.appendChild(detailLink);
            }

            body.appendChild(btnRow);

            card.appendChild(body);
            col.appendChild(card);
            container.appendChild(col);
        });
    },
});
