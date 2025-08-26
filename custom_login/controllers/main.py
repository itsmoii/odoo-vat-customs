from odoo.addons.web.controllers.home import Home
from odoo import http
from odoo.http import request

class CustomWebLogin(Home):

    @http.route('/web/login', type='http', auth='public', website=True, sitemap=False)
    def web_login(self, redirect=None, **kw):
        response = super(CustomWebLogin, self).web_login(redirect=redirect, **kw)

        # If response is a page (not a redirect), inject roles into qcontext
        if hasattr(response, 'qcontext'):
            response.qcontext['roles'] = ['Cashier', 'Manager', 'Admin']

        return response
