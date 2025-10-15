from odoo import models, fields, api


class StockPickingFinance(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super().button_validate()
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('finance_core.auto_bill_on_receipt') != 'True':
            return res
        for picking in self:
            if picking.picking_type_code != 'incoming':
                continue
            purchase_orders = picking.move_ids_without_package.mapped('purchase_line_id.order_id')
            for po in purchase_orders:
                if po.state in ('purchase', 'done') and po.invoice_status != 'invoiced':
                    # Create vendor bill in draft for received qty
                    if hasattr(po, '_create_invoices'):
                        inv = po._create_invoices(final=False)
                    elif hasattr(po, 'action_create_invoice'):
                        inv = po.action_create_invoice()
                    else:
                        continue
        return res

