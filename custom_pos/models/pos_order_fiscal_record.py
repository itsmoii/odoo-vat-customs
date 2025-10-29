from odoo import fields, models, api

class PosOrderFiscalRecord(models.Model):
    _name = "pos.order.fiscal.record"
    _description = "TaxCore Payload"

    order_id = fields.Many2one(
        "pos.order",
        required=True,
        ondelete="cascade",
        index=True,
    )

    payload = fields.Json(string="TaxCore Payload")
    invoice_number = fields.Text(string="Invoice Number")
    received_at = fields.Datetime(
        default=fields.Datetime.now,
        readonly=True,
    )
    sdc_invoice = fields.Text(string="SDC Invoice Number", required=True)
    invoice_label = fields.Text(string="Invoice Label")

    @api.model 
    def get_invoice_number(self, order_id):
        record = self.search([("order_id", "=", order_id)], limit=1)
        return record.invoice_number if record else False
    
    @api.model 
    def get_created_time(self, order_id):
        record = self.search([("order_id", "=", order_id)], limit=1)
        return record.received_at if record else False
    
    @api.model
    def get_sdc_invoice(self, order_id):
        record = self.search([("order_id", "=", order_id)], limit=1)
        return record.sdc_invoice if record else False
    
    @api.model
    def get_invoice_label(self, order_id):
        record = self.search([("order_id", "=", order_id)], limit=1)
        return record.invoice_label if record else False
    



class PosOrder(models.Model):
    _inherit = "pos.order"

    def _process_order(self, order, existing_order):
        payload = order.pop("taxcore_payload")
        invoiceNum = order.pop("invoice_number")
        sdcInvoice = order.pop("sdc_invoice")
        invLabel = order.pop("invoice_label")
        order_id = super()._process_order(order, existing_order)
        if payload:
            self.env["pos.order.fiscal.record"].create({
                "order_id": order_id,
                "payload": payload,
                "invoice_number": invoiceNum,
                "sdc_invoice": sdcInvoice,
                "invoice_label": invLabel,
            })
        return order_id