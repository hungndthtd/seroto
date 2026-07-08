import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { BuilderAction } from "@html_builder/core/builder_action";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { BaseOptionComponent } from "@html_builder/core/utils";

// 1. OWL Option component to render the custom button in Odoo 19 Sidebar
export class LayeredTextOption extends BaseOptionComponent {
    static template = "vtt_website_custom.LayeredTextOptionSidebar";
    static selector = ".s_layered_text_section";
}

// 2. OWL Dialog Component for Snippet Layer Config
export class LayerEditorModal extends Component {
    static template = "vtt_website_custom.LayerEditorModal";
    static props = {
        editingElement: Object,
        initialConfig: Array,
        close: Function,
    };

    setup() {
        this.state = useState({
            layers: this.props.initialConfig.map(l => ({ ...l })) || [],
            selectedLayerId: this.props.initialConfig.length ? this.props.initialConfig[0].id : null,
            activeTab: "editor",
            librarySvgs: [],
            selectedLibSvgId: "",
            newSvgName: "",
            newSvgColor: "#333333",
            newSvgCode: "",
        });

        // Backup existing HTML inner structure of decorative layers for cancellation
        const layersContainer = this.props.editingElement.querySelector(".s_layered_text_layers");
        this.originalHtml = layersContainer ? layersContainer.innerHTML : "";

        // Preload saved SVGs
        onWillStart(async () => {
            await this.loadLibrarySvgs();
        });

        // Drag handlers
        let isDragging = false;
        let startX = 0, startY = 0;
        let modalX = 0, modalY = 0;
        let modalEl, headerEl;

        const onMouseDown = (e) => {
            if (e.button !== 0 || e.target.closest("button") || e.target.closest("a") || e.target.closest("ul")) return;
            modalEl = document.querySelector(".modal-dialog");
            headerEl = document.querySelector(".modal-header");
            if (!modalEl) return;
            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;
            const rect = modalEl.getBoundingClientRect();
            modalX = rect.left;
            modalY = rect.top;
            modalEl.style.position = "absolute";
            modalEl.style.margin = "0";
            modalEl.style.left = `${modalX}px`;
            modalEl.style.top = `${modalY}px`;
            modalEl.style.transform = "none";
        };

        const onMouseMove = (e) => {
            if (!isDragging || !modalEl) return;
            const dx = e.clientX - startX;
            const dy = e.clientY - startY;
            modalEl.style.left = `${modalX + dx}px`;
            modalEl.style.top = `${modalY + dy}px`;
        };

        const onMouseUp = () => {
            isDragging = false;
        };

        onMounted(() => {
            const hEl = document.querySelector(".modal-header");
            if (hEl) {
                hEl.style.cursor = "move";
                hEl.addEventListener("mousedown", onMouseDown);
            }
            document.addEventListener("mousemove", onMouseMove);
            document.addEventListener("mouseup", onMouseUp);
        });

        onWillUnmount(() => {
            const hEl = document.querySelector(".modal-header");
            if (hEl) {
                hEl.removeEventListener("mousedown", onMouseDown);
            }
            document.removeEventListener("mousemove", onMouseMove);
            document.removeEventListener("mouseup", onMouseUp);
        });
    }

    // ======================== Tab switching ========================
    switchTab(tab) {
        this.state.activeTab = tab;
    }

    // ======================== SVG Library management ========================
    async loadLibrarySvgs() {
        try {
            const svgs = await rpc("/website_custom/get_svgs", {});
            if (Array.isArray(svgs)) {
                this.state.librarySvgs = svgs;
            }
        } catch (err) {
            console.error("Failed to load SVG library:", err);
        }
    }

    selectLibrarySvg(ev) {
        const svgId = ev.target.value;
        this.state.selectedLibSvgId = svgId;
        if (!svgId) return;

        const record = this.state.librarySvgs.find(s => s.id == svgId);
        if (record) {
            const selected = this.getSelectedLayer();
            if (selected && selected.type === "svg") {
                selected.customSvgCode = record.svg_code;
                selected.color = record.color || "#333333";
                this.updatePreview();
            }
        }
    }

    async saveSvgToLibrary() {
        const selected = this.getSelectedLayer();
        if (!selected || selected.type !== "svg" || !selected.customSvgCode) {
            alert(_t("Vui lòng nhập/chọn mã SVG trước khi lưu!"));
            return;
        }
        if (!this.state.newSvgName.trim()) {
            alert(_t("Vui lòng nhập tên cho mẫu SVG!"));
            return;
        }

        try {
            const result = await rpc("/website_custom/save_svg", {
                name: this.state.newSvgName,
                svg_code: selected.customSvgCode,
                color: selected.color || "#333333",
            });
            if (result.error) {
                alert(result.error);
                return;
            }
            alert(_t("Đã lưu SVG vào kho thành công!"));
            this.state.newSvgName = "";
            await this.loadLibrarySvgs();
            this.state.selectedLibSvgId = result.id;
        } catch (err) {
            console.error("Failed to save SVG to library:", err);
            alert(_t("Đã xảy ra lỗi khi lưu SVG."));
        }
    }

    async deleteLibrarySvg() {
        const svgId = this.state.selectedLibSvgId;
        if (!svgId) return;

        const record = this.state.librarySvgs.find(s => s.id == svgId);
        if (!record) return;

        if (!confirm(_t(`Bạn có chắc chắn muốn xóa SVG "${record.name}" khỏi kho?`))) return;

        try {
            const result = await rpc("/website_custom/delete_svg", { svg_id: svgId });
            if (result.error) {
                alert(result.error);
                return;
            }
            this.state.selectedLibSvgId = "";
            await this.loadLibrarySvgs();
        } catch (err) {
            console.error("Failed to delete SVG:", err);
            alert(_t("Đã xảy ra lỗi khi xóa SVG."));
        }
    }

    getSvgPreviewStyle(svgRecord) {
        try {
            let code = svgRecord.svg_code.trim();
            const rawColor = svgRecord.color || "#333333";
            
            code = code
                .replace(/fill=(?!"none")["'][^"']+["']/gi, "")
                .replace(/stroke=(?!"none")["'][^"']+["']/gi, "");

            if (code.includes("<symbol") || code.includes("<SYMBOL")) {
                const viewBoxMatch = code.match(/viewBox=["']([^"']+)["']/i);
                const viewBox = viewBoxMatch ? viewBoxMatch[1] : "0 0 150 150";
                const innerContent = code.replace(/<symbol[^>]*>/i, "").replace(/<\/symbol>/i, "");
                code = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox}"><g fill="${rawColor}" stroke="${rawColor}">${innerContent}</g></svg>`;
            } else if (code.includes("<svg") || code.includes("<SVG")) {
                const viewBoxMatch = code.match(/viewBox=["']([^"']+)["']/i);
                const viewBox = viewBoxMatch ? viewBoxMatch[1] : "0 0 100 100";
                const innerContent = code.replace(/<svg[^>]*>/i, "").replace(/<\/svg>/i, "");
                code = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox}"><g fill="${rawColor}" stroke="${rawColor}">${innerContent}</g></svg>`;
            } else {
                code = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><g fill="${rawColor}" stroke="${rawColor}">${code}</g></svg>`;
            }
            const encoded = encodeURIComponent(code);
            return `background-image: url("data:image/svg+xml;charset=utf-8,${encoded}"); background-repeat: no-repeat; background-position: center; background-size: contain; padding: 10px;`;
        } catch (e) {
            console.error("Preview render failed:", e);
            return `background-color: #fafafa;`;
        }
    }

    async updateSvgColorInLibrary(svg, ev) {
        const newColor = ev.target.value;
        try {
            await rpc("/website_custom/update_svg_color", {
                svg_id: svg.id,
                color: newColor,
            });
            svg.color = newColor;
            this.updatePreview();
        } catch (err) {
            console.error("Failed to update SVG color:", err);
            alert(_t("Đã xảy ra lỗi khi cập nhật màu SVG."));
        }
    }

    applyLibrarySvgFromTab(svg) {
        let selected = this.getSelectedLayer();
        if (!selected || selected.type !== "svg") {
            this.addLayer("svg");
            selected = this.getSelectedLayer();
        }
        if (selected) {
            selected.customSvgCode = svg.svg_code;
            selected.color = svg.color || "#333333";
            this.state.selectedLibSvgId = svg.id;
            this.state.activeTab = "editor";
            this.updatePreview();
        }
    }

    async addSvgToLibraryFromTab() {
        if (!this.state.newSvgName.trim()) {
            alert(_t("Vui lòng nhập tên họa tiết SVG!"));
            return;
        }
        if (!this.state.newSvgCode.trim()) {
            alert(_t("Vui lòng nhập mã SVG trước khi lưu!"));
            return;
        }

        try {
            const result = await rpc("/website_custom/save_svg", {
                name: this.state.newSvgName,
                svg_code: this.state.newSvgCode,
                color: this.state.newSvgColor,
            });
            if (result.error) {
                alert(result.error);
                return;
            }
            alert(_t("Đã lưu mẫu SVG mới vào kho thành công!"));
            this.state.newSvgName = "";
            this.state.newSvgCode = "";
            this.state.newSvgColor = "#333333";
            await this.loadLibrarySvgs();
        } catch (err) {
            console.error("Failed to add SVG to library:", err);
            alert(_t("Đã xảy ra lỗi khi lưu SVG vào kho."));
        }
    }

    async deleteLibrarySvgFromTab(svg) {
        if (!confirm(_t(`Bạn có chắc chắn muốn xóa SVG "${svg.name}" khỏi kho?`))) return;
        try {
            const result = await rpc("/website_custom/delete_svg", { svg_id: svg.id });
            if (result.error) {
                alert(result.error);
                return;
            }
            if (this.state.selectedLibSvgId == svg.id) {
                this.state.selectedLibSvgId = "";
            }
            await this.loadLibrarySvgs();
        } catch (err) {
            console.error("Failed to delete SVG from tab:", err);
            alert(_t("Đã xảy ra lỗi khi xóa SVG."));
        }
    }

    // ======================== Position slider helpers ========================
    getPositionXPercent(layer) {
        if (!layer.positionX) return 50;
        const val = parseInt(layer.positionX.replace(/[^0-9.-]/g, ""), 10);
        return isNaN(val) ? 50 : val;
    }

    getPositionYPercent(layer) {
        if (!layer.positionY) return 50;
        const val = parseInt(layer.positionY.replace(/[^0-9.-]/g, ""), 10);
        return isNaN(val) ? 50 : val;
    }

    updatePositionXFromSlider(layer, ev) {
        layer.positionX = ev.target.value + "%";
        this.updatePreview();
    }

    updatePositionYFromSlider(layer, ev) {
        layer.positionY = ev.target.value + "%";
        this.updatePreview();
    }

    // ======================== Layer management ========================
    addLayer(type) {
        const id = "layer_" + Date.now() + "_" + Math.random().toString(36).substr(2, 5);
        let properties = {};

        if (type === "image") {
            properties = { src: "", scale: 100, angle: 0, opacity: 100, positionX: "50%", positionY: "50%" };
        } else if (type === "svg") {
            properties = { customSvgCode: "", color: "#333333", scale: 50, angle: 0, opacity: 100, positionX: "50%", positionY: "50%" };
        } else if (type === "text") {
            properties = { text: "Text Layer", color: "#333333", fontSize: 24, fontFamily: "inherit", fontWeight: "normal", fontStyle: "normal", scale: 100, angle: 0, opacity: 100, positionX: "50%", positionY: "50%" };
        }

        const newLayer = {
            id: id,
            type: type,
            visible: true,
            ...properties,
        };

        this.state.layers.push(newLayer);
        this.state.selectedLayerId = id;
        this.updatePreview();
    }

    removeLayer(id) {
        this.state.layers = this.state.layers.filter(l => l.id !== id);
        if (this.state.selectedLayerId === id) {
            this.state.selectedLayerId = this.state.layers.length ? this.state.layers[0].id : null;
        }
        this.updatePreview();
    }

    moveLayer(id, direction) {
        const index = this.state.layers.findIndex(l => l.id === id);
        if (index === -1) return;
        const newIndex = index + direction;
        if (newIndex < 0 || newIndex >= this.state.layers.length) return;
        const temp = this.state.layers[index];
        this.state.layers[index] = this.state.layers[newIndex];
        this.state.layers[newIndex] = temp;
        this.updatePreview();
    }

    toggleLayerVisibility(id) {
        const layer = this.state.layers.find(l => l.id === id);
        if (layer) {
            layer.visible = !layer.visible;
            this.updatePreview();
        }
    }

    selectLayer(id) {
        this.state.selectedLayerId = id;
    }

    getSelectedLayer() {
        return this.state.layers.find(l => l.id === this.state.selectedLayerId);
    }

    getLayerIcon(type) {
        switch (type) {
            case "image": return "fa-picture-o";
            case "svg": return "fa-cubes";
            case "text": return "fa-font";
            default: return "fa-layer-group";
        }
    }

    getLayerName(layer) {
        switch (layer.type) {
            case "image": return `Ảnh: ${layer.src ? layer.src.split("/").pop() : "Chưa chọn"}`;
            case "svg": return `Họa tiết SVG`;
            case "text": return `Chữ: "${layer.text}"`;
            default: return "Lớp trang trí";
        }
    }

    // ======================== HTML Compiler & Renderer ========================
    compileLayerHtml(l) {
        if (!l.visible) return "";

        const opacity = (l.opacity !== undefined ? l.opacity : 100) / 100;
        const angle = l.angle || 0;
        const scale = (l.scale !== undefined ? l.scale : 100) / 100;
        const posX = l.positionX || "50%";
        const posY = l.positionY || "50%";

        const style = `position: absolute; left: ${posX}; top: ${posY}; transform: translate(-50%, -50%) rotate(${angle}deg) scale(${scale}); opacity: ${opacity}; pointer-events: none; z-index: ${l.layerPosition === 'front' ? 2 : 0};`;

        if (l.type === "image" && l.src) {
            return `<img src="${l.src}" style="${style}" class="deco-layer-item deco-image"/>`;
        } 
        else if (l.type === "svg" && l.customSvgCode) {
            let svgCode = l.customSvgCode.trim();
            const rawColor = l.color || "#333333";

            // Clean fill/stroke
            svgCode = svgCode
                .replace(/fill=(?!"none")["'][^"']+["']/gi, "")
                .replace(/stroke=(?!"none")["'][^"']+["']/gi, "");

            if (svgCode.includes("<symbol") || svgCode.includes("<SYMBOL")) {
                const viewBoxMatch = svgCode.match(/viewBox=["']([^"']+)["']/i);
                const viewBox = viewBoxMatch ? viewBoxMatch[1] : "0 0 150 150";
                const innerContent = svgCode.replace(/<symbol[^>]*>/i, "").replace(/<\/symbol>$/i, "");
                svgCode = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox}" style="${style} width: 100px; height: 100px;" class="deco-layer-item deco-svg"><g fill="${rawColor}" stroke="${rawColor}">${innerContent}</g></svg>`;
            } else if (svgCode.includes("<svg") || svgCode.includes("<SVG")) {
                const viewBoxMatch = svgCode.match(/viewBox=["']([^"']+)["']/i);
                const viewBox = viewBoxMatch ? viewBoxMatch[1] : "0 0 100 100";
                const innerContent = svgCode.replace(/<svg[^>]*>/i, "").replace(/<\/symbol>$/, "").replace(/<\/svg>$/, "");
                svgCode = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox}" style="${style} width: 100px; height: 100px;" class="deco-layer-item deco-svg"><g fill="${rawColor}" stroke="${rawColor}">${innerContent}</g></svg>`;
            } else {
                svgCode = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" style="${style} width: 100px; height: 100px;" class="deco-layer-item deco-svg"><g fill="${rawColor}" stroke="${rawColor}">${svgCode}</g></svg>`;
            }
            return svgCode;
        } 
        else if (l.type === "text" && l.text) {
            const fontStyle = `font-family: ${l.fontFamily || 'inherit'}; font-size: ${l.fontSize || 24}px; color: ${l.color || '#333333'}; font-weight: ${l.fontWeight || 'normal'}; font-style: ${l.fontStyle || 'normal'}; white-space: nowrap;`;
            return `<span style="${style} ${fontStyle}" class="deco-layer-item deco-text">${l.text}</span>`;
        }

        return "";
    }

    updatePreview() {
        const layersContainer = this.props.editingElement.querySelector(".s_layered_text_layers");
        if (!layersContainer) return;
        
        const htmlParts = this.state.layers.map(l => this.compileLayerHtml(l));
        layersContainer.innerHTML = htmlParts.join("");
    }

    applyToElement() {
        const layersContainer = this.props.editingElement.querySelector(".s_layered_text_layers");
        if (layersContainer) {
            layersContainer.dataset.layeredConfig = JSON.stringify(this.state.layers);
        }
        this.updatePreview();
        this.props.close();
    }

    cancel() {
        const layersContainer = this.props.editingElement.querySelector(".s_layered_text_layers");
        if (layersContainer) {
            layersContainer.innerHTML = this.originalHtml;
        }
        this.props.close();
    }

    openImageManager() {
        this.env.services.media.openMediaDialog({
            visibleTabs: ["images"],
            save: (media) => {
                const img = media.querySelector("img");
                if (img && img.src) {
                    const selected = this.getSelectedLayer();
                    if (selected && selected.type === "image") {
                        selected.src = img.src;
                        this.updatePreview();
                    }
                }
            }
        });
    }
}

// 3. Define the openLayerEditor Action
export class OpenLayerEditorAction extends BuilderAction {
    static id = "openLayerEditor";

    apply({ editingElement }) {
        const layersContainer = editingElement.querySelector(".s_layered_text_layers");
        const initialConfig = (layersContainer && layersContainer.dataset.layeredConfig) ? JSON.parse(layersContainer.dataset.layeredConfig) : [];
        
        const dialogService = this.services.dialog || this.env.services.dialog;
        dialogService.add(LayerEditorModal, {
            editingElement: editingElement,
            initialConfig: initialConfig,
            close: () => {},
        });
    }
}

// 4. Custom Snippet Plugin
class WebsiteLayeredTextPlugin extends Plugin {
    static id = "websiteLayeredTextPlugin";
    static dependencies = ["media"];
    
    setup() {
        const doc = this.document || (this.env && this.env.document) || document;
        if (!doc) return;

        // Auto-compile layers when editor opens
        try {
            const sections = doc.querySelectorAll(".s_layered_text_section");
            sections.forEach(sec => {
                const layersContainer = sec.querySelector(".s_layered_text_layers");
                if (layersContainer && layersContainer.dataset.layeredConfig) {
                    const layers = JSON.parse(layersContainer.dataset.layeredConfig);
                    const htmlParts = layers.map(l => {
                        const opacity = (l.opacity !== undefined ? l.opacity : 100) / 100;
                        const angle = l.angle || 0;
                        const scale = (l.scale !== undefined ? l.scale : 100) / 100;
                        const posX = l.positionX || "50%";
                        const posY = l.positionY || "50%";

                        const style = `position: absolute; left: ${posX}; top: ${posY}; transform: translate(-50%, -50%) rotate(${angle}deg) scale(${scale}); opacity: ${opacity}; pointer-events: none; z-index: ${l.layerPosition === 'front' ? 2 : 0};`;

                        if (l.type === "image" && l.src) {
                            return `<img src="${l.src}" style="${style}" class="deco-layer-item deco-image"/>`;
                        } 
                        else if (l.type === "svg" && l.customSvgCode) {
                            let svgCode = l.customSvgCode.trim();
                            const rawColor = l.color || "#333333";

                            svgCode = svgCode
                                .replace(/fill=(?!"none")["'][^"']+["']/gi, "")
                                .replace(/stroke=(?!"none")["'][^"']+["']/gi, "");

                            if (svgCode.includes("<symbol") || svgCode.includes("<SYMBOL")) {
                                const viewBoxMatch = svgCode.match(/viewBox=["']([^"']+)["']/i);
                                const viewBox = viewBoxMatch ? viewBoxMatch[1] : "0 0 150 150";
                                const innerContent = svgCode.replace(/<symbol[^>]*>/i, "").replace(/<\/symbol>$/i, "");
                                svgCode = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox}" style="${style} width: 100px; height: 100px;" class="deco-layer-item deco-svg"><g fill="${rawColor}" stroke="${rawColor}">${innerContent}</g></svg>`;
                            } else if (svgCode.includes("<svg") || svgCode.includes("<SVG")) {
                                const viewBoxMatch = svgCode.match(/viewBox=["']([^"']+)["']/i);
                                const viewBox = viewBoxMatch ? viewBoxMatch[1] : "0 0 100 100";
                                const innerContent = svgCode.replace(/<svg[^>]*>/i, "").replace(/<\/symbol>$/, "").replace(/<\/svg>$/, "");
                                svgCode = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox}" style="${style} width: 100px; height: 100px;" class="deco-layer-item deco-svg"><g fill="${rawColor}" stroke="${rawColor}">${innerContent}</g></svg>`;
                            } else {
                                svgCode = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" style="${style} width: 100px; height: 100px;" class="deco-layer-item deco-svg"><g fill="${rawColor}" stroke="${rawColor}">${svgCode}</g></svg>`;
                            }
                            return svgCode;
                        } 
                        else if (l.type === "text" && l.text) {
                            const fontStyle = `font-family: ${l.fontFamily || 'inherit'}; font-size: ${l.fontSize || 24}px; color: ${l.color || '#333333'}; font-weight: ${l.fontWeight || 'normal'}; font-style: ${l.fontStyle || 'normal'}; white-space: nowrap;`;
                            return `<span style="${style} ${fontStyle}" class="deco-layer-item deco-text">${l.text}</span>`;
                        }
                        return "";
                    });
                    layersContainer.innerHTML = htmlParts.join("");
                }
            });
        } catch (e) {
            console.warn("VTT Layered Text loading skipped:", e);
        }
    }

    resources = {
        builder_actions: {
            OpenLayerEditorAction,
        },
        builder_options: [
            LayeredTextOption,
        ]
    };
}

registry.category("website-plugins").add(WebsiteLayeredTextPlugin.id, WebsiteLayeredTextPlugin);
