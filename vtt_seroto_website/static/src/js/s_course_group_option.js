/** @odoo-module **/

import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { BEGIN } from "@html_builder/utils/option_sequence";

// Thêm ô nhập "Mã đối tượng" vào panel Tùy chỉnh cho snippet "Khóa học - Nhóm đối
// tượng" (views/snippets/trang_chu/s_trang_chu_course_group.xml) - lưu vào
// data-audience-code trên khối gốc (dataAttributeAction -> editingElement.dataset.
// audienceCode), đọc lại bởi static/src/js/course_group_snippet.js lúc tải trang để
// lọc đúng khóa học theo academic.course.audience_ids.code.
export class CourseGroupOption extends BaseOptionComponent {
    static template = "vtt_seroto_website.CourseGroupOption";
    static selector = ".s_trang_chu_course_group";
}

class CourseGroupOptionPlugin extends Plugin {
    static id = "courseGroupOption";
    resources = {
        builder_options: [withSequence(BEGIN, CourseGroupOption)],
    };
}

registry.category("website-plugins").add(CourseGroupOptionPlugin.id, CourseGroupOptionPlugin);
