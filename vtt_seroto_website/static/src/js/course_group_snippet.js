/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

// Tạo <i class="fa {iconClass}"/> dùng cho các dòng icon trong .item__info-content -
// cùng vai trò các <svg> tĩnh trong s_trang_chu_course.xml, nhưng dùng FontAwesome cho
// gọn (khớp cách course_snippet.js/s_course_card.xml đã làm) thay vì nhúng path SVG dài.
function _makeIcon(iconClass) {
    const wrap = document.createElement("div");
    const icon = document.createElement("i");
    icon.className = `fa ${iconClass}`;
    wrap.appendChild(icon);
    return wrap;
}

// Widget cho snippet "Khóa học - Nhóm đối tượng"
// (views/snippets/trang_chu/s_trang_chu_course_group.xml) - đọc Mã đối tượng từ
// data-audience-code (nhập ở panel Tùy chỉnh, xem s_course_group_option.xml), gọi API
// lấy khóa học khớp academic.course.audience_ids.code, tự dựng .course__box-item bằng
// createElement/textContent (không dùng innerHTML nối chuỗi - tránh XSS nếu tên/mô tả
// khóa học chứa ký tự HTML đặc biệt) - MỖI LẦN TẢI TRANG, nên đổi dữ liệu Khóa học
// trong backend hoặc nâng cấp module là web tự cập nhật, không cần xóa kéo lại snippet.
publicWidget.registry.SerotoCourseGroupSnippet = publicWidget.Widget.extend({

    selector: ".s_trang_chu_course_group",

    start() {
        this._super(...arguments);
        this._loadCourses().catch(console.error);
        return this;
    },

    async _loadCourses() {
        const audienceCode = this.el.dataset.audienceCode || null;
        const courses = await rpc("/seroto/academic-course/list", { audience_code: audienceCode });
        this._renderCourses(courses);
    },

    _renderCourses(courses) {
        const container = this.el.querySelector(".js_course_container");

        if (!container) {
            console.warn("Seroto: .js_course_container not found");
            return;
        }

        container.innerHTML = "";

        courses.forEach((course) => {
            const col = document.createElement("div");
            col.className = "col-12 col-md-4 mb-4 mb-md-0";

            const item = document.createElement("div");
            item.className = "course__box-item";

            const imageWrap = document.createElement("div");
            imageWrap.className = "item__image";
            const img = document.createElement("img");
            img.className = "img-fluid";
            img.style.maxHeight = "170px";
            img.style.width = "100%";
            img.src = course.image_url;
            img.alt = course.name;
            imageWrap.appendChild(img);
            item.appendChild(imageWrap);

            const body = document.createElement("div");
            body.style.padding = "16px 12px";
            body.style.display = "flex";
            body.style.flexDirection = "column";
            body.style.height = "100%";
            body.style.flex = "1";

            const title = document.createElement("div");
            title.className = "item__title";
            title.textContent = course.name;
            body.appendChild(title);

            if (course.slogan) {
                const subtitle = document.createElement("div");
                subtitle.className = "item__subtitle";
                subtitle.textContent = course.slogan;
                body.appendChild(subtitle);
            }

            const tag = document.createElement("div");
            tag.className = "item__tag";
            if (course.format.toLowerCase().includes("offline")) {
                tag.classList.add("green");
            }
            tag.textContent = course.format || "Online Zoom";
            body.appendChild(tag);

            const info = document.createElement("div");
            info.className = "item__info";

            // options.boldValue: in đậm (kèm .text-red nếu options.red) TOÀN BỘ value -
            // khớp <b class="text-red">...</b> trong s_trang_chu_course.xml (Ngày học/
            // Thời gian/Thời hạn đăng ký).
            // options.boldSuffix: chỉ in đậm phần MÃ ĐỢT ở cuối chuỗi (vd "K19" trong
            // "Đang mở đăng ký K19") - khớp <b>K19</b> (không màu) của dòng Tuyển sinh.
            const addInfoLine = (iconClass, label, value, options = {}) => {
                if (!value) {
                    return;
                }
                const line = document.createElement("div");
                line.className = "item__info-content";
                line.appendChild(_makeIcon(iconClass));

                const p = document.createElement("p");
                if (label) {
                    p.appendChild(document.createTextNode(`${label}: `));
                }

                if (options.boldValue) {
                    const b = document.createElement("b");
                    if (options.red) {
                        b.className = "text-red";
                    }
                    b.textContent = value;
                    p.appendChild(b);
                } else if (options.boldSuffix) {
                    const match = value.match(/^(.*?)(\s*)(K\d+)$/);
                    if (match) {
                        p.appendChild(document.createTextNode(match[1] + match[2]));
                        const b = document.createElement("b");
                        b.textContent = match[3];
                        p.appendChild(b);
                    } else {
                        p.appendChild(document.createTextNode(value));
                    }
                } else {
                    p.appendChild(document.createTextNode(value));
                }

                line.appendChild(p);
                info.appendChild(line);
            };

            addInfoLine("fa-user", null, course.lecturer);
            addInfoLine("fa-info-circle", "Tuyển sinh", course.batch_info, { boldSuffix: true });
            addInfoLine("fa-calendar", "Ngày học", course.schedule_date, { boldValue: true, red: true });
            addInfoLine("fa-clock-o", "Thời gian", course.schedule_time, { boldValue: true, red: true });
            addInfoLine(
                "fa-hourglass-half", "Thời hạn đăng ký", course.deadline_register,
                { boldValue: true, red: true }
            );
            body.appendChild(info);

            const buttonRow = document.createElement("div");
            buttonRow.className = "item__button";

            const registerBtn = document.createElement("div");
            registerBtn.className = "item__button-action fill";
            if (course.is_registration_open) {
                registerBtn.classList.add("js_register_course_wizard");
                registerBtn.dataset.course = course.name;
                registerBtn.textContent = "Đăng ký ngay";
            } else {
                registerBtn.textContent = "Sắp mở đăng ký";
                registerBtn.style.opacity = "0.6";
                registerBtn.style.cursor = "not-allowed";
            }
            buttonRow.appendChild(registerBtn);

            // Chỉ hiện khi khóa học có Link chi tiết (field detail_url,
            // academic.course) - target="_blank": mở trang chi tiết ở tab mới, không
            // mất trang đang xem, khớp <a target="_blank"> trong s_trang_chu_course.xml.
            if (course.detail_url) {
                const detailLink = document.createElement("a");
                detailLink.className = "item__button-action outline";
                detailLink.href = course.detail_url;
                detailLink.target = "_blank";
                detailLink.rel = "noopener";
                detailLink.textContent = "Chi tiết";
                buttonRow.appendChild(detailLink);
            }

            body.appendChild(buttonRow);

            item.appendChild(body);
            col.appendChild(item);
            container.appendChild(col);
        });
    },

});
