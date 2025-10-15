from odoo import models, fields


class TaxBulkWizard(models.TransientModel):
    _name = 'tax.bulk.wizard'
    _description = 'Bulk Apply or Remove Taxes'

    tax_id = fields.Many2one('account.tax', string="Tax to Apply", required=True,
                             domain="[('type_tax_use','=','sale')]")
    action_type = fields.Selection([
        ('apply', 'Apply Tax'),
        ('remove', 'Remove Tax')
    ], string="Action", required=True, default='apply')

    def action_confirm(self):
        active_ids = self.env.context.get('active_ids', [])
        if not active_ids:
            return {'type': 'ir.actions.act_window_close'}

        products = self.env['product.template'].browse(active_ids)
        for product in products:
            if self.action_type == 'apply':
                product.taxes_id = [(6, 0, [self.tax_id.id])]
            else:
                product.taxes_id = [(5, 0, 0)]

        return {'type': 'ir.actions.act_window_close'}

