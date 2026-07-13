import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class SerotoShapeOption extends BaseOptionComponent {
    static template = "seroto_education.SerotoShapeOption";
    static selector = ".s_seroto_svg_shape, .s_seroto_svg_shape *";

    setShape(shapeId) {
        const activeElement = this.env.getEditingElement();
        if (!activeElement) {
            return;
        }
        
        const element = activeElement.closest(".s_seroto_svg_shape") || activeElement;
        const useTag = element.querySelector("use");
        if (useTag) {
            useTag.setAttribute("xlink:href", `#${shapeId}`);
            useTag.setAttribute("href", `#${shapeId}`);
        }
        
        const doc = element.ownerDocument;
        const symbol = doc.getElementById(shapeId);
        if (symbol) {
            const svgTag = element.querySelector("svg");
            if (svgTag) {
                const viewBox = symbol.getAttribute("viewBox");
                if (viewBox) {
                    svgTag.setAttribute("viewBox", viewBox);
                }
            }
        }
    }

    setSize(property, value) {
        const activeElement = this.env.getEditingElement();
        if (!activeElement) {
            return;
        }
        const element = activeElement.closest(".s_seroto_svg_shape") || activeElement;
        const container = element.querySelector(".seroto-shape-item");
        if (container) {
            container.style[property] = value;
        }
    }
}

export class SerotoTitleOption extends BaseOptionComponent {
    static template = "seroto_education.SerotoTitleOption";
    static selector = ".s_seroto_title, .s_seroto_title *";

    setFontFamily(fontName) {
        const activeElement = this.env.getEditingElement();
        if (!activeElement) {
            return;
        }
        const titleEl = activeElement.closest(".s_seroto_title") || activeElement;
        titleEl.style.fontFamily = fontName;
    }
}

class SerotoShapeOptionPlugin extends Plugin {
    static id = "serotoShapeOption";
    resources = {
        builder_options: [SerotoShapeOption, SerotoTitleOption],
    };
}

registry.category("website-plugins").add(SerotoShapeOptionPlugin.id, SerotoShapeOptionPlugin);
