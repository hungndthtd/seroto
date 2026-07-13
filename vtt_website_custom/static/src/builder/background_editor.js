import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { BuilderAction } from "@html_builder/core/builder_action";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

// 1. OWL Dialog Component for Custom Background Builder
export class BackgroundEditorModal extends Component {
    static template = "vtt_website_custom.BackgroundEditorModal";
    static props = {
        editingElement: Object,
        initialConfig: Array,
        close: Function,
    };

    setup() {
        this.state = useState({
            layers: this.props.initialConfig.map(l => ({ ...l })) || [],
            selectedLayerId: this.props.initialConfig.length ? this.props.initialConfig[0].id : null,
            templateName: "",
            activeTab: "editor",
            savedTemplates: [],
            loadingTemplates: false,
            librarySvgs: [],
            selectedLibSvgId: "",
            newSvgName: "",
            newSvgColor: "#333333",
            newSvgCode: "",
            overflow: this.props.editingElement.dataset.customBgOverflow || "visible",
        });
        
        // Backup original background style on child container to allow cancellation
        const existingBg = this.props.editingElement.querySelector(":scope > .vtt_custom_bg");
        this.originalStyle = {
            exists: !!existingBg,
            backgroundImage: existingBg ? existingBg.style.backgroundImage : "",
            backgroundPosition: existingBg ? existingBg.style.backgroundPosition : "",
            backgroundRepeat: existingBg ? existingBg.style.backgroundRepeat : "",
            backgroundSize: existingBg ? existingBg.style.backgroundSize : "",
            innerHTML: existingBg ? existingBg.innerHTML : "",
            parentPosition: this.props.editingElement.style.position || "",
            overflow: this.props.editingElement.style.overflow || "",
        };

        // Preload saved templates in the background
        onWillStart(async () => {
            await Promise.all([
                this.loadSavedTemplates(),
                this.loadLibrarySvgs()
            ]);
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
        if (tab === "templates" && this.state.savedTemplates.length === 0) {
            this.loadSavedTemplates();
        }
    }

    // ======================== Template management ========================
    async loadSavedTemplates() {
        this.state.loadingTemplates = true;
        try {
            const templates = await rpc("/website_custom/get_backgrounds", {});
            if (Array.isArray(templates)) {
                this.state.savedTemplates = templates;
            }
        } catch (err) {
            console.error("Failed to load background templates:", err);
        }
        this.state.loadingTemplates = false;
    }

    applyTemplate(tpl) {
        try {
            const layers = JSON.parse(tpl.config_json);
            this.state.layers = layers.map(l => ({ ...l }));
            this.state.selectedLayerId = layers.length ? layers[0].id : null;
            this.state.activeTab = "editor";
            this.updatePreview();
        } catch (err) {
            console.error("Failed to apply template:", err);
            alert(_t("Không thể đọc cấu hình mẫu này."));
        }
    }

    async deleteTemplate(tpl) {
        if (!confirm(_t(`Bạn có chắc chắn muốn xóa mẫu "${tpl.name}"?`))) return;
        try {
            await rpc("/website_custom/delete_background", { bg_id: tpl.id });
            this.state.savedTemplates = this.state.savedTemplates.filter(t => t.id !== tpl.id);
        } catch (err) {
            console.error("Failed to delete template:", err);
            alert(_t("Đã xảy ra lỗi khi xóa mẫu."));
        }
    }

    getTemplateLayerSummary(tpl) {
        try {
            const layers = JSON.parse(tpl.config_json);
            const counts = {};
            layers.forEach(l => {
                const type = l.type || "unknown";
                counts[type] = (counts[type] || 0) + 1;
            });
            const parts = [];
            if (counts.color) parts.push(`${counts.color} màu`);
            if (counts.gradient) parts.push(`${counts.gradient} gradient`);
            if (counts.svg) parts.push(`${counts.svg} SVG`);
            if (counts.image) parts.push(`${counts.image} ảnh`);
            return parts.join(", ") || "Trống";
        } catch {
            return "";
        }
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
            alert(_t("Vui lòng nhập mã SVG trước khi lưu!"));
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
            
            // Strip existing fill/stroke attributes (except 'none') to let dynamic color apply cleanly
            code = code
                .replace(/fill=(?!"none")["'][^"']+["']/gi, "")
                .replace(/stroke=(?!"none")["'][^"']+["']/gi, "");

            // Robust tag identification and wrapper injection
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

    applyLibrarySvgFromTab(svg) {
        let selected = this.getSelectedLayer();
        if (!selected || selected.type !== "svg") {
            this.addLayer("svg");
            selected = this.getSelectedLayer();
        }
        if (selected) {
            selected.svgType = "custom";
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

    // ======================== Layer management ========================
    addLayer(type) {
        const id = "layer_" + Date.now() + "_" + Math.random().toString(36).substr(2, 5);
        let properties = {};

        if (type === "color") {
            properties = { color: "#3a97ff" };
        } else if (type === "gradient") {
            properties = { direction: 45, colorStart: "#ff5e62", colorEnd: "#ff9966" };
        } else if (type === "svg") {
            properties = { 
                svgType: "dots", 
                color: "#333333", 
                scale: 40, 
                angle: 0,
                size: "auto",
                repeat: "repeat",
                positionType: "preset",
                position: "center",
                positionX: "50%",
                positionY: "50%",
                customSvgCode: ``
            };
        } else if (type === "image") {
            properties = { 
                src: "", 
                size: "cover", 
                repeat: "no-repeat", 
                positionType: "preset",
                position: "center",
                positionX: "50%",
                positionY: "50%",
                angle: 0,
                scale: 100,
                customWidth: "",
                customWidthUnit: "px",
                customHeight: "",
                customHeightUnit: "px"
            };
        }

        const newLayer = {
            id: id,
            type: type,
            visible: true,
            opacity: 100,
            ...properties,
        };

        this.state.layers.unshift(newLayer);
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
            case "color": return "fa-paint-brush";
            case "gradient": return "fa-sliders";
            case "svg": return "fa-cubes";
            case "image": return "fa-picture-o";
            default: return "fa-layer-group";
        }
    }

    getLayerName(layer) {
        switch (layer.type) {
            case "color": return `Màu trơn: ${layer.color}`;
            case "gradient": return `Gradient: ${layer.colorStart} ➔ ${layer.colorEnd}`;
            case "svg": return `Họa tiết SVG: ${layer.svgType}`;
            case "image": return `Ảnh: ${layer.src ? layer.src.split("/").pop() : "Chưa chọn"}`;
            default: return "Lớp nền";
        }
    }

    // ======================== CSS Compiler ========================
    compileStyles() {
        const activeLayers = this.state.layers.filter(l => l.visible);
        if (!activeLayers.length) {
            return {
                backgroundImage: "none",
                backgroundPosition: "initial",
                backgroundRepeat: "initial",
                backgroundSize: "initial",
            };
        }

        const images = [];
        const positions = [];
        const repeats = [];
        const sizes = [];

        activeLayers.forEach(l => {
            const opacity = l.opacity / 100;
            const rotation = l.angle || 0;
            
            if (l.type === "color") {
                const r = parseInt(l.color.slice(1, 3), 16);
                const g = parseInt(l.color.slice(3, 5), 16);
                const b = parseInt(l.color.slice(5, 7), 16);
                const colorStr = `rgba(${r}, ${g}, ${b}, ${opacity})`;
                images.push(`linear-gradient(${colorStr}, ${colorStr})`);
                positions.push("center");
                repeats.push("no-repeat");
                sizes.push("auto");
            } 
            else if (l.type === "gradient") {
                const rS = parseInt(l.colorStart.slice(1, 3), 16);
                const gS = parseInt(l.colorStart.slice(3, 5), 16);
                const bS = parseInt(l.colorStart.slice(5, 7), 16);
                const rE = parseInt(l.colorEnd.slice(1, 3), 16);
                const gE = parseInt(l.colorEnd.slice(3, 5), 16);
                const bE = parseInt(l.colorEnd.slice(5, 7), 16);
                const startColor = `rgba(${rS}, ${gS}, ${bS}, ${opacity})`;
                const endColor = `rgba(${rE}, ${gE}, ${bE}, ${opacity})`;
                images.push(`linear-gradient(${l.direction}deg, ${startColor}, ${endColor})`);
                positions.push("center");
                repeats.push("no-repeat");
                sizes.push("auto");
            }
            else if (l.type === "svg") {
                let svgContent = "";
                const rawColor = l.color;
                
                if (l.svgType === "dots") {
                    svgContent = `<svg xmlns="http://www.w3.org/2000/svg" width="${l.scale}" height="${l.scale}" viewBox="0 0 20 20"><g transform="rotate(${rotation}, 10, 10)"><circle cx="10" cy="10" r="2.5" fill="${rawColor}" fill-opacity="${opacity}"/></g></svg>`;
                } else if (l.svgType === "waves") {
                    svgContent = `<svg xmlns="http://www.w3.org/2000/svg" width="${l.scale * 4}" height="${l.scale}" viewBox="0 0 100 20"><g transform="rotate(${rotation}, 50, 10)"><path d="M0 10 Q25 20 50 10 T100 10" fill="none" stroke="${rawColor}" stroke-opacity="${opacity}" stroke-width="4"/></g></svg>`;
                } else if (l.svgType === "grid") {
                    svgContent = `<svg xmlns="http://www.w3.org/2000/svg" width="${l.scale}" height="${l.scale}" viewBox="0 0 20 20"><g transform="rotate(${rotation}, 10, 10)"><rect width="20" height="20" fill="none" stroke="${rawColor}" stroke-opacity="${opacity}" stroke-width="0.5"/></g></svg>`;
                } else if (l.svgType === "stripes") {
                    svgContent = `<svg xmlns="http://www.w3.org/2000/svg" width="${l.scale}" height="${l.scale}" viewBox="0 0 40 40"><g transform="rotate(${rotation}, 20, 20)"><path d="M0 40 L40 0 M-10 10 L10 -10 M30 50 L50 30" fill="none" stroke="${rawColor}" stroke-opacity="${opacity}" stroke-width="4"/></g></svg>`;
                } else if (l.svgType === "custom" && l.customSvgCode) {
                    let userSvg = l.customSvgCode.trim();
                    
                    // Strip existing fill/stroke attributes (except 'none')
                    userSvg = userSvg
                        .replace(/fill=(?!"none")["'][^"']+["']/gi, "")
                        .replace(/stroke=(?!"none")["'][^"']+["']/gi, "");
                    
                    // AUTO CONVERT <symbol> to <svg>
                    if (userSvg.includes("<symbol") || userSvg.includes("<SYMBOL")) {
                        const viewBoxMatch = userSvg.match(/viewBox=["']([^"']+)["']/i);
                        const viewBox = viewBoxMatch ? viewBoxMatch[1] : "0 0 150 150";
                        const innerContent = userSvg.replace(/<symbol[^>]*>/i, "").replace(/<\/symbol>$/i, "");
                        userSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox}" width="[scale]" height="[scale]"><g fill="[color]" fill-opacity="[opacity]" stroke="[color]" stroke-opacity="[opacity]">${innerContent}</g></svg>`;
                    }

                    if (userSvg.includes("<svg") || userSvg.includes("<SVG")) {
                        const viewBoxMatch = userSvg.match(/viewBox=["']([^"']+)["']/i);
                        const viewBox = viewBoxMatch ? viewBoxMatch[1] : "0 0 100 100";
                        const parts = viewBox.split(/\s+/).map(Number);
                        const cx = (parts.length >= 4) ? (parts[0] + parts[2] / 2) : 50;
                        const cy = (parts.length >= 4) ? (parts[1] + parts[3] / 2) : 50;
                        const innerContent = userSvg.replace(/<svg[^>]*>/i, "").replace(/<\/svg>$/, "");
                        
                        // Robust wrapper injection around clean content to apply coloring smoothly
                        userSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox}" width="[scale]" height="[scale]"><g transform="rotate(${rotation}, ${cx}, ${cy})" fill="[color]" fill-opacity="[opacity]" stroke="[color]" stroke-opacity="[opacity]">${innerContent}</g></svg>`;
                        svgContent = userSvg
                            .replace(/\[color\]/g, rawColor)
                            .replace(/\[opacity\]/g, opacity)
                            .replace(/\[scale\]/g, l.scale);
                    } else {
                        svgContent = `<svg xmlns="http://www.w3.org/2000/svg" width="${l.scale}" height="${l.scale}" viewBox="0 0 20 20"><g fill="${rawColor}" stroke="${rawColor}" fill-opacity="${opacity}" stroke-opacity="${opacity}" transform="rotate(${rotation}, 10, 10)">${userSvg}</g></svg>`;
                    }
                }

                const encoded = encodeURIComponent(svgContent);
                images.push(`url("data:image/svg+xml;charset=utf-8,${encoded}")`);
                const pos = (l.positionType === "custom") ? `${l.positionX || "50%"} ${l.positionY || "50%"}` : (l.position || "center");
                positions.push(pos);
                repeats.push(l.repeat || "repeat");
                sizes.push(l.size || "auto");
            }
            else if (l.type === "image" && l.src) {
                images.push(`linear-gradient(rgba(255,255,255,${opacity - 1}), rgba(255,255,255,${opacity - 1})), url("${l.src}")`);
                const pos = (l.positionType === "custom") ? `${l.positionX || "50%"} ${l.positionY || "50%"}` : (l.position || "center");
                positions.push(`${pos}, ${pos}`);
                repeats.push(`${l.repeat}, ${l.repeat}`);
                
                let sizeVal = l.size || "cover";
                if (sizeVal === "custom") {
                    if (l.customWidth || l.customHeight) {
                        const w = l.customWidth ? `${l.customWidth}${l.customWidthUnit || "px"}` : "auto";
                        const h = l.customHeight ? `${l.customHeight}${l.customHeightUnit || "px"}` : "auto";
                        sizeVal = `${w} ${h}`;
                    } else if (l.scale) {
                        sizeVal = `${l.scale}%`;
                    }
                }
                sizes.push(`${sizeVal}, ${sizeVal}`);
            }
        });

        return {
            backgroundImage: images.join(", "),
            backgroundPosition: positions.join(", "),
            backgroundRepeat: repeats.join(", "),
            backgroundSize: sizes.join(", "),
        };
    }

    // ======================== Preview & Apply ========================
    getOrCreateBgContainer() {
        const el = this.props.editingElement;
        let bgContainer = el.querySelector(":scope > .vtt_custom_bg");
        if (!bgContainer) {
            bgContainer = document.createElement("div");
            bgContainer.className = "vtt_custom_bg";
            bgContainer.style.position = "absolute";
            bgContainer.style.top = "0";
            bgContainer.style.left = "0";
            bgContainer.style.right = "0";
            bgContainer.style.bottom = "0";
            bgContainer.style.pointerEvents = "none";
            bgContainer.style.zIndex = "0";
            if (window.getComputedStyle(el).position === "static") {
                el.style.position = "relative";
            }
            el.insertBefore(bgContainer, el.firstChild);
        }
        return bgContainer;
    }

    renderBgLayers(bgContainer, layers) {
        bgContainer.innerHTML = "";
        const activeLayers = [...layers].filter(l => l.visible).reverse();
        
        activeLayers.forEach(l => {
            const opacity = l.opacity !== undefined ? l.opacity / 100 : 1;
            const rotation = l.angle || 0;
            
            const layerEl = document.createElement("div");
            layerEl.className = "vtt_custom_bg_layer";
            layerEl.style.position = "absolute";
            layerEl.style.top = "0";
            layerEl.style.left = "0";
            layerEl.style.right = "0";
            layerEl.style.bottom = "0";
            layerEl.style.pointerEvents = "none";
            layerEl.style.opacity = opacity;
            
            if (rotation) {
                layerEl.style.transform = `rotate(${rotation}deg)`;
            }
            
            if (l.type === "color") {
                layerEl.style.backgroundColor = l.color;
            } 
            else if (l.type === "gradient") {
                layerEl.style.backgroundImage = `linear-gradient(${l.direction}deg, ${l.colorStart}, ${l.colorEnd})`;
            }
            else if (l.type === "svg") {
                let svgContent = "";
                const rawColor = l.color;
                
                if (l.svgType === "dots") {
                    svgContent = `<svg xmlns="http://www.w3.org/2000/svg" width="${l.scale}" height="${l.scale}" viewBox="0 0 20 20"><circle cx="10" cy="10" r="2.5" fill="${rawColor}"/></svg>`;
                } else if (l.svgType === "waves") {
                    svgContent = `<svg xmlns="http://www.w3.org/2000/svg" width="${l.scale * 4}" height="${l.scale}" viewBox="0 0 100 20"><path d="M0 10 Q25 20 50 10 T100 10" fill="none" stroke="${rawColor}" stroke-width="4"/></svg>`;
                } else if (l.svgType === "grid") {
                    svgContent = `<svg xmlns="http://www.w3.org/2000/svg" width="${l.scale}" height="${l.scale}" viewBox="0 0 20 20"><rect width="20" height="20" fill="none" stroke="${rawColor}" stroke-width="0.5"/></svg>`;
                } else if (l.svgType === "stripes") {
                    svgContent = `<svg xmlns="http://www.w3.org/2000/svg" width="${l.scale}" height="${l.scale}" viewBox="0 0 40 40"><path d="M0 40 L40 0 M-10 10 L10 -10 M30 50 L50 30" fill="none" stroke="${rawColor}" stroke-width="4"/></svg>`;
                } else if (l.svgType === "custom" && l.customSvgCode) {
                    let userSvg = l.customSvgCode.trim();
                    userSvg = userSvg
                        .replace(/fill=(?!"none")["'][^"']+["']/gi, "")
                        .replace(/stroke=(?!"none")["'][^"']+["']/gi, "");
                    
                    if (userSvg.includes("<symbol") || userSvg.includes("<SYMBOL")) {
                        const viewBoxMatch = userSvg.match(/viewBox=["']([^"']+)["']/i);
                        const viewBox = viewBoxMatch ? viewBoxMatch[1] : "0 0 150 150";
                        const innerContent = userSvg.replace(/<symbol[^>]*>/i, "").replace(/<\/symbol>$/i, "");
                        userSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox}" width="${l.scale}" height="${l.scale}"><g fill="${rawColor}" stroke="${rawColor}">${innerContent}</g></svg>`;
                    } else if (userSvg.includes("<svg") || userSvg.includes("<SVG")) {
                        const viewBoxMatch = userSvg.match(/viewBox=["']([^"']+)["']/i);
                        const viewBox = viewBoxMatch ? viewBoxMatch[1] : "0 0 100 100";
                        const innerContent = userSvg.replace(/<svg[^>]*>/i, "").replace(/<\/symbol>$/, "").replace(/<\/svg>$/, "");
                        userSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox}" width="${l.scale}" height="${l.scale}"><g fill="${rawColor}" stroke="${rawColor}">${innerContent}</g></svg>`;
                    } else {
                        userSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="${l.scale}" height="${l.scale}" viewBox="0 0 20 20"><g fill="${rawColor}" stroke="${rawColor}">${userSvg}</g></svg>`;
                    }
                    svgContent = userSvg;
                }
                const encoded = encodeURIComponent(svgContent);
                layerEl.style.backgroundImage = `url("data:image/svg+xml;charset=utf-8,${encoded}")`;
                const pos = (l.positionType === "custom") ? `${l.positionX || "50%"} ${l.positionY || "50%"}` : (l.position || "center");
                layerEl.style.backgroundPosition = pos;
                layerEl.style.backgroundRepeat = l.repeat || "repeat";
                layerEl.style.backgroundSize = l.size || "auto";
                
                // Set transform-origin to match background-position to prevent shifting
                layerEl.style.transformOrigin = pos;
            }
            else if (l.type === "image" && l.src) {
                layerEl.style.backgroundImage = `url("${l.src}")`;
                const pos = (l.positionType === "custom") ? `${l.positionX || "50%"} ${l.positionY || "50%"}` : (l.position || "center");
                layerEl.style.backgroundPosition = pos;
                layerEl.style.backgroundRepeat = l.repeat || "no-repeat";
                
                let sizeVal = l.size || "cover";
                if (sizeVal === "custom") {
                    if (l.customWidth || l.customHeight) {
                        const w = l.customWidth ? `${l.customWidth}${l.customWidthUnit || "px"}` : "auto";
                        const h = l.customHeight ? `${l.customHeight}${l.customHeightUnit || "px"}` : "auto";
                        sizeVal = `${w} ${h}`;
                    } else if (l.scale) {
                        sizeVal = `${l.scale}%`;
                    }
                }
                layerEl.style.backgroundSize = sizeVal;
                
                // Set transform-origin to match background-position to prevent shifting
                layerEl.style.transformOrigin = pos;
            }
            
            bgContainer.appendChild(layerEl);
        });
    }

    updatePreview() {
        const bgContainer = this.getOrCreateBgContainer();
        this.renderBgLayers(bgContainer, this.state.layers);
        
        // Clean parent styles to prevent Odoo parser crash
        const el = this.props.editingElement;
        el.style.backgroundImage = "";
        el.style.backgroundPosition = "";
        el.style.backgroundRepeat = "";
        el.style.backgroundSize = "";
        el.style.overflow = this.state.overflow;
    }

    applyToSection() {
        this.props.editingElement.dataset.customBgConfig = JSON.stringify(this.state.layers);
        this.props.editingElement.dataset.customBgOverflow = this.state.overflow;
        this.props.close();
    }

    cancel() {
        const el = this.props.editingElement;
        const bgContainer = el.querySelector(":scope > .vtt_custom_bg");
        if (this.originalStyle.exists) {
            if (bgContainer) {
                bgContainer.innerHTML = this.originalStyle.innerHTML;
                bgContainer.style.backgroundImage = this.originalStyle.backgroundImage;
                bgContainer.style.backgroundPosition = this.originalStyle.backgroundPosition;
                bgContainer.style.backgroundRepeat = this.originalStyle.backgroundRepeat;
                bgContainer.style.backgroundSize = this.originalStyle.backgroundSize;
            }
            el.style.overflow = this.originalStyle.overflow;
        } else {
            if (bgContainer) bgContainer.remove();
            el.style.position = this.originalStyle.parentPosition;
            el.style.overflow = this.originalStyle.overflow;
        }
        this.props.close();
    }

    async saveAsTemplate() {
        if (!this.state.templateName.trim()) {
            alert(_t("Vui lòng nhập tên mẫu hình nền để lưu!"));
            return;
        }
        try {
            const styles = this.compileStyles();
            const configJson = JSON.stringify(this.state.layers);
            const compiledCss = `background-image: ${styles.backgroundImage}; background-position: ${styles.backgroundPosition}; background-repeat: ${styles.backgroundRepeat}; background-size: ${styles.backgroundSize};`;
            const result = await rpc("/website_custom/save_background", {
                name: this.state.templateName,
                config_json: configJson,
                compiled_css: compiledCss,
            });
            if (result.error) { alert(result.error); return; }
            alert(_t("Đã lưu mẫu hình nền thành công!"));
            // Refresh saved templates list
            await this.loadSavedTemplates();
            this.applyToSection();
        } catch (err) {
            console.error("Error saving background:", err);
            alert(_t("Đã xảy ra lỗi khi lưu mẫu hình nền."));
        }
    }

    openImageManager() {
        if (window.vttMediaService) {
            window.vttMediaService.openMediaDialog({
                visibleTabs: ["IMAGES"],
                save: (media) => {
                    let src = "";
                    if (media) {
                        if (media.tagName === "IMG") {
                            src = media.src || media.getAttribute("src");
                        } else {
                            const img = media.querySelector("img");
                            if (img) {
                                src = img.src || img.getAttribute("src");
                            }
                        }
                    }
                    if (src) {
                        const selected = this.getSelectedLayer();
                        if (selected && selected.type === "image") {
                            selected.src = src;
                            this.updatePreview();
                        }
                    }
                }
            });
        } else {
            console.error("VTT Media Service not available on window");
        }
    }
}

// 2. Define the Custom Background Builder Action
export class OpenCustomBackgroundBuilderAction extends BuilderAction {
    static id = "openCustomBackgroundBuilder";
    static dependencies = ["dialog", "media"];

    apply({ editingElement }) {
        const initialConfig = editingElement.dataset.customBgConfig ? JSON.parse(editingElement.dataset.customBgConfig) : [];
        const actionInstance = this.action || this;
        const dialogService = actionInstance.services.dialog;
        dialogService.add(BackgroundEditorModal, {
            editingElement: editingElement,
            initialConfig: initialConfig,
            close: () => {},
        });
    }
}

// 3. Custom Plugin
class WebsiteCustomBackgroundPlugin extends Plugin {
    static id = "websiteCustomBackgroundPlugin";
    static dependencies = ["media"];
    
    setup() {
        window.vttMediaService = this.dependencies.media;
        
        // Safely find the document context
        const doc = this.document || (this.env && this.env.document) || document;
        if (!doc) return;

        // Auto-migration: move old multi-layer styles from parent to child container
        try {
            const elements = doc.querySelectorAll("[data-custom-bg-config]");
            elements.forEach(el => {
                if (el.dataset.customBgOverflow) {
                    el.style.overflow = el.dataset.customBgOverflow;
                }
                if (el.style.backgroundImage && el.style.backgroundImage.includes(",")) {
                    let bgContainer = el.querySelector(":scope > .vtt_custom_bg");
                    if (!bgContainer) {
                        bgContainer = doc.createElement("div");
                        bgContainer.className = "vtt_custom_bg";
                        bgContainer.style.position = "absolute";
                        bgContainer.style.top = "0";
                        bgContainer.style.left = "0";
                        bgContainer.style.right = "0";
                        bgContainer.style.bottom = "0";
                        bgContainer.style.pointerEvents = "none";
                        bgContainer.style.zIndex = "0";
                        if (window.getComputedStyle(el).position === "static") {
                            el.style.position = "relative";
                        }
                        el.insertBefore(bgContainer, el.firstChild);
                    }
                    bgContainer.style.backgroundImage = el.style.backgroundImage;
                    bgContainer.style.backgroundPosition = el.style.backgroundPosition;
                    bgContainer.style.backgroundRepeat = el.style.backgroundRepeat;
                    bgContainer.style.backgroundSize = el.style.backgroundSize;
                    el.style.backgroundImage = "";
                    el.style.backgroundPosition = "";
                    el.style.backgroundRepeat = "";
                    el.style.backgroundSize = "";
                }
            });
        } catch (e) {
            console.warn("VTT Custom Background migration skipped:", e);
        }
    }
    
    resources = {
        builder_actions: {
            OpenCustomBackgroundBuilderAction,
        }
    };
}

registry.category("website-plugins").add(WebsiteCustomBackgroundPlugin.id, WebsiteCustomBackgroundPlugin);
