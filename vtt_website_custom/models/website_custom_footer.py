# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class WebsiteCustomFooter(models.Model):
    _name = 'website.custom.footer'
    _description = 'Custom Website Footer Template'
    _order = 'id desc'

    name = fields.Char(string='Name', required=True)
    website_id = fields.Many2one('website', string='Website', default=lambda self: self.env['website'].get_current_website(), required=True, ondelete='cascade')
    arch = fields.Text(string='Architecture', required=True)
    view_id = fields.Many2one('ir.ui.view', string='Associated View', ondelete='cascade')

    @api.model_create_multi
    def create(self, vals_list):
        records = super(WebsiteCustomFooter, self).create(vals_list)
        for record in records:
            # Create corresponding ir.ui.view for Odoo QWeb engine (strip website_id from context to prevent generic view creation error)
            view_vals = {
                'name': f"Custom Footer: {record.name}",
                'type': 'qweb',
                'inherit_id': self.env.ref('website.layout').id,
                'website_id': record.website_id.id,
                'key': f'vtt_website_custom.template_footer_custom_{record.id}',
                'arch': record.arch,
                'active': False,
            }
            view = self.env['ir.ui.view'].with_context(website_id=None).create(view_vals)
            # Link view back to the custom footer record (using write to avoid recursion during create)
            record.write({'view_id': view.id})
        return records

    def write(self, vals):
        res = super(WebsiteCustomFooter, self).write(vals)
        if 'arch' in vals or 'name' in vals:
            for record in self:
                if record.view_id:
                    view_vals = {}
                    if 'arch' in vals and record.view_id.arch != record.arch:
                        view_vals['arch'] = record.arch
                    if 'name' in vals:
                        view_vals['name'] = f"Custom Footer: {record.name}"
                    if view_vals:
                        record.view_id.with_context(website_id=None).write(view_vals)
        return res

class WebsitePage(models.Model):
    _inherit = 'website.page'

    footer_view_id = fields.Many2one('ir.ui.view', string='Page Footer Template', ondelete='set null')
    parent_footer_template_id = fields.Many2one('website.custom.footer', string='Parent Custom Footer Template', ondelete='set null')
    footer_template_key = fields.Char(string='Footer Template Key')

class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    def write(self, vals):
        # Bypass Odoo's Copy-On-Write (COW) mechanism for our private page-specific and template views
        is_custom = any(view.key and (view.key.startswith('vtt_website_custom.page_footer_') or 
                                      view.key.startswith('vtt_website_custom.template_footer_custom_')) 
                        for view in self)
        if is_custom:
            self = self.with_context(no_cow=True)

        res = super(IrUiView, self).write(vals)
        
        if 'arch' in vals:
            for view in self:
                # Only propagate back to custom footer if it is a template view (not a page-specific view)
                if view.key and view.key.startswith('vtt_website_custom.template_footer_custom_'):
                    custom_footers = self.env['website.custom.footer'].sudo().search([('view_id', '=', view.id)])
                    for footer in custom_footers:
                        if footer.arch != view.arch:
                            super(WebsiteCustomFooter, footer).write({'arch': view.arch})
        return res

    def _render_template(self, template, values=None):
        if values is None:
            values = {}
        main_object = values.get('main_object')
        
        # Read the page-specific footer view key & template key
        footer_template_key = None
        if main_object and main_object._name == 'website.page':
            page_sudo = main_object.sudo().with_context(active_test=False)
            if page_sudo.footer_view_id:
                footer_id = page_sudo.footer_view_id.id
                self = self.with_context(page_footer_view_id=footer_id)
                if request:
                    request.update_context(page_footer_view_id=footer_id)
            footer_template_key = page_sudo.footer_template_key
                
        # If no template key is set on page, fallback to the website's default active footer key
        if not footer_template_key:
            layout_view = self.env.ref('website.layout', raise_if_not_found=False)
            if layout_view:
                current_website = self.env['website'].get_current_website()
                inherited_views = self.env['ir.ui.view'].sudo().search([
                    ('inherit_id', '=', layout_view.id),
                    ('active', '=', True),
                    ('website_id', 'in', [current_website.id, False]),
                ])
                for view in inherited_views:
                    if view.arch and ('//div[@id=\'footer\']' in view.arch or '//div[@id="footer"]' in view.arch):
                        footer_template_key = view.key
                        break
            if not footer_template_key:
                footer_template_key = 'website.footer_custom'
                
        values['page_footer_key'] = footer_template_key
        values['footer_template_key'] = footer_template_key
                
        return super(IrUiView, self)._render_template(template, values=values)

    def _get_inheriting_views(self):
        page_footer_view_id = self.env.context.get('page_footer_view_id')
        
        # Only apply our custom logic if we are resolving inheriting views for website.layout
        layout_view = self.env.ref('website.layout', raise_if_not_found=False)
        is_layout = layout_view and layout_view.id in self.ids
        
        if page_footer_view_id and is_layout:
            views = super(IrUiView, self)._get_inheriting_views()
            
            # Get IDs of custom footers views and standard ones to filter them out
            custom_footer_view_ids = self.env['website.custom.footer'].sudo().search([]).mapped('view_id.id')
            standard_footer_keys = [
                'website.footer_custom',
                'website.template_footer_descriptive',
                'website.template_footer_centered',
                'website.template_footer_links',
                'website.template_footer_minimalist',
                'website.template_footer_contact',
                'website.template_footer_call_to_action',
                'website.template_footer_headline',
                'website.template_footer_mega',
                'website.template_footer_mega_columns',
                'website.template_footer_mega_links',
                'website.template_footer_mega_cards',
            ]
            standard_footer_views = self.env['ir.ui.view'].sudo().search([('key', 'in', standard_footer_keys)])
            all_footer_view_ids = set(custom_footer_view_ids + standard_footer_views.ids)
            
            # Filter views
            filtered_views = self.env['ir.ui.view']
            for v in views:
                if v.id not in all_footer_view_ids:
                    filtered_views |= v
            
            # Force add the target page footer template
            target_view = self.env['ir.ui.view'].sudo().browse(page_footer_view_id)
            if target_view.exists():
                filtered_views |= target_view
                
            return filtered_views

        return super(IrUiView, self)._get_inheriting_views()

class IrQweb(models.AbstractModel):
    _inherit = 'ir.qweb'

    def _get_template_cache_keys(self):
        # Extend cache keys to ensure different page footers compile into separate cache entries
        return super(IrQweb, self)._get_template_cache_keys() + ['page_footer_view_id']
