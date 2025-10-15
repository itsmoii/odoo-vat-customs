from odoo import api, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for config in records:
            cash_methods = config.payment_method_ids.filtered('is_cash_count')
            if cash_methods and set(cash_methods.ids) != set(config.payment_method_ids.ids):
                config.with_context(custom_pos_cash_only=True).write({
                    'payment_method_ids': [(6, 0, cash_methods.ids)],
                })
        return records

    def write(self, vals):
        res = super().write(vals)
        # Enforce cash-only after any change to payment methods
        if 'payment_method_ids' in vals and not self.env.context.get('custom_pos_cash_only'):
            for config in self:
                cash_methods = config.payment_method_ids.filtered('is_cash_count')
                if cash_methods and set(cash_methods.ids) != set(config.payment_method_ids.ids):
                    config.with_context(custom_pos_cash_only=True).write({
                        'payment_method_ids': [(6, 0, cash_methods.ids)],
                    })
        return res

