import { patch } from "@web/core/utils/patch";
import { FooterTemplateOption, FooterTemplateChoice } from "@website/builder/plugins/options/footer_template_option";
import { WebsiteConfigFooterAction } from "@website/builder/plugins/options/footer_option_plugin";
import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { useState } from "@odoo/owl";

// 1. Ensure savePlugin is in FooterTemplateOption dependencies so we can trigger page save
if (FooterTemplateOption.dependencies && !FooterTemplateOption.dependencies.includes("savePlugin")) {
    FooterTemplateOption.dependencies.push("savePlugin");
}

// 2. Patch the FooterTemplateOption component to add custom footer saving & resetting logic
patch(FooterTemplateOption.prototype, {
    setup() {
        super.setup();
        this.state = useState({
            hasTemplate: false,
            templateName: "",
        });

        // Load the page footer template status
        const websiteService = this.services.website;
        const mainObject = websiteService && websiteService.currentWebsite && websiteService.currentWebsite.metadata.mainObject;
        if (mainObject && mainObject.model === "website.page") {
            const pageId = mainObject.id;
            rpc("/website_custom/get_page_footer_status", { page_id: pageId }).then((status) => {
                this.state.hasTemplate = status.has_template;
                this.state.templateName = status.template_name;
            }).catch((err) => {
                console.error("Error loading page footer status:", err);
            });
        }
    },

    async saveToCurrentTemplate() {
        try {
            // Save pending editor changes first
            if (this.dependencies.savePlugin) {
                await this.dependencies.savePlugin.save();
            }

            const websiteService = this.services.website;
            const mainObject = websiteService && websiteService.currentWebsite && websiteService.currentWebsite.metadata.mainObject;
            const pageId = (mainObject && mainObject.model === "website.page") ? mainObject.id : null;

            if (!pageId) {
                alert(_t("Không xác định được trang hiện tại để cập nhật mẫu."));
                return;
            }

            const result = await rpc("/website_custom/save_to_current_template", {
                page_id: pageId
            });

            if (result.error) {
                alert(result.error);
                return;
            }

            alert(_t("Đã cập nhật thay đổi vào mẫu hiện tại thành công!"));
            window.location.reload();
        } catch (err) {
            console.error(err);
            alert(_t("Đã xảy ra lỗi khi cập nhật mẫu."));
        }
    },

    async saveCustomFooter() {
        const name = prompt(_t("Nhập tên cho mẫu Footer mới:"));
        if (!name) {
            return;
        }

        try {
            // Save pending editor changes first
            if (this.dependencies.savePlugin) {
                await this.dependencies.savePlugin.save();
            }

            // Get current page ID if available
            const websiteService = this.services.website;
            const mainObject = websiteService && websiteService.currentWebsite && websiteService.currentWebsite.metadata.mainObject;
            const pageId = (mainObject && mainObject.model === "website.page") ? mainObject.id : null;

            // Call RPC to save the custom footer view
            const result = await rpc("/website_custom/save_footer", {
                name: name,
                page_id: pageId,
            });

            if (result.error) {
                alert(result.error);
                return;
            }

            alert(_t("Đã lưu mẫu Footer mới thành công!"));
            
            // Reload the editor page to compile and apply the new templates
            window.location.reload();
        } catch (err) {
            console.error(err);
            alert(_t("Đã xảy ra lỗi khi lưu mẫu Footer."));
        }
    },

    async resetToGlobalFooter() {
        try {
            const websiteService = this.services.website;
            const mainObject = websiteService && websiteService.currentWebsite && websiteService.currentWebsite.metadata.mainObject;
            const pageId = (mainObject && mainObject.model === "website.page") ? mainObject.id : null;

            if (!pageId) {
                alert(_t("Không xác định được trang hiện tại để cài lại Footer chung."));
                return;
            }

            if (confirm(_t("Bạn có chắc chắn muốn đặt lại Footer của trang này về Footer chung của Website?"))) {
                const result = await rpc("/website_custom/update_page_footer", {
                    page_id: pageId,
                    view_key: false, // clear page footer to fallback to global
                });

                if (result.error) {
                    alert(result.error);
                    return;
                }

                alert(_t("Đã đặt lại về Footer chung thành công!"));
                window.location.reload();
            }
        } catch (err) {
            console.error(err);
            alert(_t("Đã xảy ra lỗi khi hoàn tác về Footer chung."));
        }
    }
});

// 3. Patch WebsiteConfigFooterAction to intercept footer template selection and active status checkmark (V icon)
patch(WebsiteConfigFooterAction.prototype, {
    isApplied({ params: { vars, view }, selectableContext }) {
        const websiteService = this.services.website;
        const mainObject = websiteService && websiteService.currentWebsite && websiteService.currentWebsite.metadata.mainObject;
        
        if (mainObject && mainObject.model === "website.page") {
            // Read footer template key directly from html DOM attribute
            const currentFooterKey = this.document.documentElement.dataset.footerTemplateKey;
            return currentFooterKey === view;
        }

        // Fallback to standard Odoo logic for global actions
        return super.isApplied(...arguments);
    },

    async apply({ params: { vars, view }, selectableContext }) {
        const websiteService = this.services.website; // Access via this.services instead of this.env.services
        const mainObject = websiteService && websiteService.currentWebsite && websiteService.currentWebsite.metadata.mainObject;
        
        if (mainObject && mainObject.model === "website.page") {
            const pageId = mainObject.id;
            try {
                // Call our custom RPC to update the page-specific footer view instead of globally
                const result = await rpc("/website_custom/update_page_footer", {
                    page_id: pageId,
                    view_key: view,
                });
                if (result.error) {
                    alert(result.error);
                    return;
                }
                // Reload page to compile and render page-specific footer
                window.location.reload();
                return;
            } catch (err) {
                console.error("Error setting page footer:", err);
                alert(_t("Lỗi khi áp dụng Footer cho trang này."));
                return;
            }
        }

        // Fallback to global behavior if not on a website page
        return super.apply(...arguments);
    }
});

// 4. Define and register a custom plugin to load custom footer templates from backend
class CustomFooterOptionPlugin extends Plugin {
    static id = "customFooterOption";

    resources = {
        footer_templates_providers: [
            () => this.getCustomFooterTemplates(),
        ],
    };

    async getCustomFooterTemplates() {
        try {
            const customFooters = await rpc("/website_custom/get_custom_footers");
            return customFooters.map((info) => ({
                key: info.view_key,
                Component: FooterTemplateChoice,
                props: {
                    imgSrc: `/website/static/src/img/snippets_options/footer_template_default.svg`,
                    varName: info.view_key,
                    view: info.view_key,
                    title: info.name,
                },
            }));
        } catch (err) {
            console.error("Error fetching custom footer templates:", err);
            return [];
        }
    }
}

registry.category("website-plugins").add(CustomFooterOptionPlugin.id, CustomFooterOptionPlugin);
