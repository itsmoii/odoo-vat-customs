from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def _get_closed_orders(self):
        """Exclude proforma/training/advance orders from session posting."""
        orders = super()._get_closed_orders()
        return orders.filtered(
            lambda o: not (
                getattr(o, "is_proforma", False)
                or getattr(o, "is_training", False)
            )
        )
