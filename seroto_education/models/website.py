# -*- coding: utf-8 -*-

from odoo import models, fields

class Website(models.Model):
    _inherit = 'website'

    def _control_third_party_trackers_in_html(self, html):
        # Workaround fallback for database version mismatch (restored from server)
        return html
