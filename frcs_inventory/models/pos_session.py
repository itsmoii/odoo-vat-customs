from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_product_product(self):
        params = super()._loader_params_product_product()
        fields = params.get('search_params', {}).get('fields', [])
        # Ensure both aliases are sent to the frontend
        for f in ('total_price', 'x_total_price'):
            if f not in fields:
                fields.append(f)
        params['search_params']['fields'] = fields
        return params

