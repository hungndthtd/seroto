# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class WebsiteCustomController(http.Controller):

    @http.route('/website_custom/save_footer', type='jsonrpc', auth='user', website=True)
    def save_footer(self, name, page_id=None):
        try:
            website = request.website
            active_footer_view = None
            page = None
            
            # 1. If page_id is provided, get the page-specific footer view
            if page_id:
                page = request.env['website.page'].browse(int(page_id))
                if page.exists() and page.footer_view_id:
                    active_footer_view = page.footer_view_id

            # 2. Fallback to active template if no page-specific view exists
            if not active_footer_view:
                layout_view = request.env.ref('website.layout')
                inherited_views = request.env['ir.ui.view'].search([
                    ('inherit_id', '=', layout_view.id),
                    ('active', '=', True),
                    ('website_id', 'in', [website.id, False]),
                ])
                for view in inherited_views:
                    if view.arch and ('//div[@id=\'footer\']' in view.arch or '//div[@id="footer"]' in view.arch):
                        active_footer_view = view
                        break

            # 3. Fallback to default active footer_custom
            if not active_footer_view:
                fallback_view = request.env['ir.ui.view'].search([
                    ('key', '=', 'website.footer_custom'),
                    ('website_id', 'in', [website.id, False]),
                ], limit=1)
                if fallback_view:
                    active_footer_view = fallback_view

            if not active_footer_view:
                return {'error': 'No active footer template found to save.'}

            # Create new custom template with copied arch (strip website_id from environment context)
            custom_footer = request.env['website.custom.footer'].with_context(website_id=None).create({
                'name': name,
                'website_id': website.id,
                'arch': active_footer_view.arch,
            })

            # Link current page to this newly created template
            if page and page.exists():
                page.write({
                    'parent_footer_template_id': custom_footer.id,
                    'footer_template_key': custom_footer.view_id.key
                })

            return {
                'success': True,
                'view_key': custom_footer.view_id.key,
                'name': custom_footer.name,
                'id': custom_footer.id,
            }
        except Exception as e:
            _logger.exception("EXCEPTION IN SAVE_FOOTER:")
            return {'error': str(e)}

    @http.route('/website_custom/save_to_current_template', type='jsonrpc', auth='user', website=True)
    def save_to_current_template(self, page_id):
        try:
            page = request.env['website.page'].browse(int(page_id))
            if not page.exists():
                return {'error': 'Page not found.'}
                
            if not page.parent_footer_template_id:
                return {'error': 'No current template associated with this page.'}
                
            if not page.footer_view_id:
                return {'error': 'No customized footer found on this page to save.'}
                
            # Overwrite the template's arch with the page's current footer arch (strip website_id context)
            page.parent_footer_template_id.with_context(website_id=None).write({
                'arch': page.footer_view_id.arch
            })
            return {'success': True}
        except Exception as e:
            _logger.exception("EXCEPTION IN SAVE_TO_CURRENT_TEMPLATE:")
            return {'error': str(e)}

    @http.route('/website_custom/get_page_footer_status', type='jsonrpc', auth='user', website=True)
    def get_page_footer_status(self, page_id):
        try:
            page = request.env['website.page'].browse(int(page_id))
            if page.exists() and page.parent_footer_template_id:
                return {
                    'has_template': True,
                    'template_name': page.parent_footer_template_id.name,
                }
            return {'has_template': False}
        except Exception as e:
            _logger.exception("EXCEPTION IN GET_PAGE_FOOTER_STATUS:")
            return {'error': str(e)}

    @http.route('/website_custom/update_page_footer', type='jsonrpc', auth='user', website=True)
    def update_page_footer(self, page_id, view_key):
        try:
            page = request.env['website.page'].browse(int(page_id))
            if not page.exists():
                return {'error': 'Page not found.'}
                
            _logger.warning("UPDATE_PAGE_FOOTER: page_id=%s, view_key=%s, page_website_id=%s", page_id, view_key, page.website_id.id)
                
            if not view_key:
                # Revert to global website default footer
                page.write({
                    'footer_view_id': False,
                    'parent_footer_template_id': False,
                    'footer_template_key': False
                })
                return {'success': True}

            selected_view = None
            
            # 1. Check custom footers
            parent_template = None
            if isinstance(view_key, str) and view_key.startswith('vtt_website_custom.template_footer_custom_'):
                try:
                    footer_id = int(view_key.split('_')[-1])
                    footer_record = request.env['website.custom.footer'].sudo().browse(footer_id)
                    if footer_record.exists() and footer_record.view_id:
                        selected_view = footer_record.view_id
                        parent_template = footer_record
                except Exception as e:
                    _logger.error("Failed to parse custom footer ID from key %s: %s", view_key, e)

            # 2. Try XML ID / Ref
            if not selected_view and '.' in view_key:
                try:
                    selected_view = request.env.ref(view_key)
                    if selected_view and selected_view._name != 'ir.ui.view':
                        selected_view = None
                except Exception:
                    pass
                    
            # 3. Search key with website constraint
            if not selected_view:
                selected_view = request.env['ir.ui.view'].search([
                    ('key', '=', view_key),
                    ('website_id', 'in', [page.website_id.id, False])
                ], order='website_id desc', limit=1)
                
            # 4. Search key without website constraint (fallback)
            if not selected_view:
                selected_view = request.env['ir.ui.view'].search([
                    ('key', '=', view_key)
                ], order='website_id desc', limit=1)

            if not selected_view:
                _logger.error("UPDATE_PAGE_FOOTER: View not found for key %s", view_key)
                return {'error': 'Footer template view not found.'}
                
            # Set parent custom template and footer_template_key
            page.write({
                'parent_footer_template_id': parent_template.id if parent_template else False,
                'footer_template_key': view_key
            })
            
            # Copy the selected template's arch into a page-specific private view
            # Ensure we always create a new page-specific view if the key isn't page_footer_{id}
            # Strip website_id context to prevent Odoo generic view constraint check error
            page_view = page.footer_view_id
            is_page_specific = page_view and page_view.key and page_view.key.startswith('vtt_website_custom.page_footer_')
            
            if not is_page_specific:
                page_view = request.env['ir.ui.view'].with_context(website_id=None).create({
                    'name': f"Page Footer: {page.url}",
                    'type': 'qweb',
                    'inherit_id': request.env.ref('website.layout').id,
                    'website_id': page.website_id.id or False,
                    'key': f'vtt_website_custom.page_footer_{page.id}',
                    'arch': selected_view.arch,
                    'active': False,
                })
                page.write({'footer_view_id': page_view.id})
            else:
                page_view.with_context(website_id=None).write({
                    'arch': selected_view.arch
                })
                
            return {'success': True}
        except Exception as e:
            _logger.exception("EXCEPTION IN UPDATE_PAGE_FOOTER:")
            return {'error': str(e)}

    @http.route('/website_custom/get_custom_footers', type='jsonrpc', auth='user', website=True)
    def get_custom_footers(self):
        try:
            website = request.website
            footers = request.env['website.custom.footer'].search([
                ('website_id', 'in', [website.id, False])
            ])
            return [{
                'id': footer.id,
                'name': footer.name,
                'view_key': footer.view_id.key,
            } for footer in footers]
        except Exception as e:
            _logger.exception("EXCEPTION IN GET_CUSTOM_FOOTERS:")
            return {'error': str(e)}

    @http.route('/website_custom/save_background', type='jsonrpc', auth='user', website=True)
    def save_background(self, name, config_json, compiled_css, compiled_svg=None):
        try:
            website = request.website
            # Use sudo() to bypass access constraints for designers creating templates
            background = request.env['website.custom.background'].sudo().create({
                'name': name,
                'website_id': website.id,
                'config_json': config_json,
                'compiled_css': compiled_css,
                'compiled_svg': compiled_svg
            })
            return {
                'success': True,
                'id': background.id,
                'name': background.name,
            }
        except Exception as e:
            _logger.exception("EXCEPTION IN SAVE_BACKGROUND:")
            return {'error': str(e)}

    @http.route('/website_custom/get_backgrounds', type='jsonrpc', auth='user', website=True)
    def get_backgrounds(self):
        try:
            website = request.website
            # Use sudo() to bypass access constraints
            backgrounds = request.env['website.custom.background'].sudo().search([
                ('website_id', 'in', [website.id, False])
            ])
            return [{
                'id': bg.id,
                'name': bg.name,
                'config_json': bg.config_json,
                'compiled_css': bg.compiled_css,
                'compiled_svg': bg.compiled_svg,
            } for bg in backgrounds]
        except Exception as e:
            _logger.exception("EXCEPTION IN GET_BACKGROUNDS:")
            return {'error': str(e)}

    @http.route('/website_custom/delete_background', type='jsonrpc', auth='user', website=True)
    def delete_background(self, bg_id):
        try:
            background = request.env['website.custom.background'].sudo().browse(int(bg_id))
            if background.exists():
                background.unlink()
                return {'success': True}
            return {'error': 'Background template not found.'}
        except Exception as e:
            _logger.exception("EXCEPTION IN DELETE_BACKGROUND:")
            return {'error': str(e)}

    @http.route('/website_custom/save_svg', type='jsonrpc', auth='user', website=True)
    def save_svg(self, name, svg_code, color='#333333'):
        try:
            website = request.website
            svg_record = request.env['website.custom.svg'].sudo().create({
                'name': name,
                'svg_code': svg_code,
                'color': color,
                'website_id': website.id,
            })
            return {
                'success': True,
                'id': svg_record.id,
                'name': svg_record.name,
            }
        except Exception as e:
            _logger.exception("EXCEPTION IN SAVE_SVG:")
            return {'error': str(e)}

    @http.route('/website_custom/get_svgs', type='jsonrpc', auth='user', website=True)
    def get_svgs(self):
        try:
            website = request.website
            svg_records = request.env['website.custom.svg'].sudo().search([
                ('website_id', 'in', [website.id, False])
            ])
            return [{
                'id': rec.id,
                'name': rec.name,
                'svg_code': rec.svg_code,
                'color': rec.color or '#333333',
            } for rec in svg_records]
        except Exception as e:
            _logger.exception("EXCEPTION IN GET_SVGS:")
            return {'error': str(e)}

    @http.route('/website_custom/update_svg_color', type='jsonrpc', auth='user', website=True)
    def update_svg_color(self, svg_id, color):
        try:
            svg_record = request.env['website.custom.svg'].sudo().browse(int(svg_id))
            if svg_record.exists():
                svg_record.write({'color': color})
                return {'success': True}
            return {'error': 'SVG asset not found.'}
        except Exception as e:
            _logger.exception("EXCEPTION IN UPDATE_SVG_COLOR:")
            return {'error': str(e)}

    @http.route('/website_custom/delete_svg', type='jsonrpc', auth='user', website=True)
    def delete_svg(self, svg_id):
        try:
            svg_record = request.env['website.custom.svg'].sudo().browse(int(svg_id))
            if svg_record.exists():
                svg_record.unlink()
                return {'success': True}
            return {'error': 'SVG asset not found.'}
        except Exception as e:
            _logger.exception("EXCEPTION IN DELETE_SVG:")
            return {'error': str(e)}
