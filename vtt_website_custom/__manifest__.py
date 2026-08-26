# -*- coding: utf-8 -*-
{
    'name': 'Custom Website Layout & Footer',
    'version': '1.0',
    'category': 'Website',
    'summary': 'Save and reuse custom website footer templates and backgrounds.',
    'description': """
This module allows saving the currently customized website footer as a template
and reusing it on other pages or websites. It also includes a custom multi-layer background builder.
    """,
    'author': 'Antigravity',
    'depends': ['website', 'website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/website_custom_footer_views.xml',
        'views/website_custom_background_views.xml',
        'views/website_custom_svg_views.xml',
        'views/website_sale_shop_footer_views.xml',
        'views/snippets.xml',
    ],
    'assets': {
        'website.website_builder_assets': [
            'vtt_website_custom/static/src/builder/footer_custom_option.xml',
            'vtt_website_custom/static/src/builder/footer_custom_option.js',
            'vtt_website_custom/static/src/builder/background_editor.xml',
            'vtt_website_custom/static/src/builder/background_editor.js',
            'vtt_website_custom/static/src/builder/layered_text.xml',
            'vtt_website_custom/static/src/builder/layered_text.js',
        ],
        'web.assets_frontend': [
            'vtt_website_custom/static/src/scss/background_editor.scss',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
