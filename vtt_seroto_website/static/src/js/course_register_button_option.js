/** @odoo-module **/

import { onWillStart, useState } from "@odoo/owl";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { BEGIN } from "@html_builder/utils/option_sequence";

// Cho phép biến BẤT KỲ nút/link nào (không chỉ các snippet dựng sẵn) thành nút mở
// modal đăng ký khóa học (course_register_wizard.js) NGAY trên panel "Tùy chỉnh" của
// Website Builder - không cần mở Code View sửa tay class/data-course như trước.
//
// Cơ chế: tick "Dùng làm nút đăng ký" -> tự gắn class "js_register_course_wizard" lên
// phần tử đang chọn (JS toàn site đã nghe sẵn click trên class này, xem
// course_register_wizard.js, gắn qua website.layout nên có ở MỌI trang) + dropdown
// "Khóa học" -> tự gắn attribute data-course = ĐÚNG academic.course.name (chọn từ danh
// sách thật, load qua ORM lúc mở panel - KHÔNG gõ tay nên không còn rủi ro gõ sai/thiếu
// dấu như trước). data-course vẫn giữ nguyên là TÊN khóa học (không đổi sang mã) để
// không phải sửa lại cách khớp khóa học ở controllers/course_registration.py.
//
// selector "a, button, .btn": áp dụng cho hầu hết nút/link thật trên site. Với 1 số
// khối "nút" dựng bằng <div class="item__button-action..."> (vd s_trang_chu_course.xml)
// không khớp selector này - cần thêm class "btn" cho khối đó, hoặc bổ sung class riêng
// vào selector bên dưới nếu phát sinh thêm kiểu nút mới.
export class CourseRegisterButtonOption extends BaseOptionComponent {
    static template = "vtt_seroto_website.CourseRegisterButtonOption";
    static selector = "a, button, .btn";

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.courseState = useState({ courses: [] });
        onWillStart(async () => {
            this.courseState.courses = await this.orm.searchRead(
                "academic.course", [], ["name"], { order: "name asc" }
            );
        });
    }
}

class CourseRegisterButtonOptionPlugin extends Plugin {
    static id = "courseRegisterButtonOption";
    resources = {
        builder_options: [withSequence(BEGIN, CourseRegisterButtonOption)],
    };
}

registry.category("website-plugins").add(CourseRegisterButtonOptionPlugin.id, CourseRegisterButtonOptionPlugin);
