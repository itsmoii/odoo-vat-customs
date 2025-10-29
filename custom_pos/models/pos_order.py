from odoo import models, fields, api

class PosOrder(models.Model):
    _inherit = "pos.order"

    invoice_label = fields.Char(string="Invoice Label")
    taxcore_journal = fields.Text(string="TaxCore Jounal")
    is_proforma = fields.Boolean(default=False)


def _enqueue_taxcore_print(self):
    for order in self:
        ip = order.config_id.raw_printer_ip
        if not ip:
            continue
        # Pick what you want to print (example uses TaxCore Journal)
        journal = None
        try:
            # If you store JSON in a field; adapt to your field name
            journal = (order.taxcore_response or {}).get('Journal')
        except Exception:
            journal = None
        if not journal:
            continue
        self.env['pos.print.job'].create({
            'order_id': order.id,
            'payload': journal,
            'printer_ip': ip,
        })

def _order_fields(self, ui_order):
    vals = super()._order_fields(ui_order)
    if ui_order.get('taxcore_journal'):
        vals['taxcore_journal'] = ui_order['taxcore_journal']
    vals['is_proforma'] = ui_order.get('is_proforma', False)
    if vals['is_proforma']:
        vals['payment_ids'] = []
        vals['amount_paid'] = 0.0
        vals['amount_return'] = 0.0
    return vals

def _create_order_picking(self):
    normal = self.filtered(lambda o: not o.is_proforma)
    if normal:
        return super(PosOrder, normal)._create_order_picking()
    return True

def _create_account_move(self):
    normal = self.filtered(lambda o: not o.is_proforma)
    if normal:
        return super(PosOrder, normal)._create_account_move()
    return False




#PRINTERRRR
def action_pos_order_paid(self):
    res = super().action_pos_order_paid()
    # enqueue print if we have a printer IP and a journal
    for order in self:
        ip = order.config_id.raw_printer_ip
        if ip and order.taxcore_journal:
            self.env['pos.print.job'].sudo().create({
                'order_id': order.id,
                'printer_ip': ip,
                'payload': order.taxcore_journal,
            })
    return res
