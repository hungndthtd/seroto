/** @odoo-module **/

import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { BEGIN } from "@html_builder/utils/option_sequence";

// Thêm mục "Căn chỉnh" (Trái/Giữa/Phải) vào panel Tùy chỉnh của Website Editor cho
// snippet "Title - Tiêu đề" (views/snippets/s_block.xml, template s_title_special).
// classAction (text-start/text-center/text-end) áp thẳng lên khối gốc .s_title_special
// - vì .title__special bên trong là display:inline-block nên text-align trên khối cha
// sẽ canh giữa/trái/phải toàn bộ tiêu đề + mũi tên.
export class TitleSpecialOption extends BaseOptionComponent {
    static template = "seroto_website.TitleSpecialOption";
    static selector = ".s_title_special";
}

class TitleSpecialOptionPlugin extends Plugin {
    static id = "titleSpecialOption";
    resources = {
        builder_options: [withSequence(BEGIN, TitleSpecialOption)],
    };
}

registry.category("website-plugins").add(TitleSpecialOptionPlugin.id, TitleSpecialOptionPlugin);
