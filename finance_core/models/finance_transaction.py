from odoo import models, fields, api

class FinanceTransaction(models.Model):
    _name = 'finance.transaction'
    _description = 'Finance Transaction'
    _order = 'date desc, id desc'

    # Use a callable for default (new API), not a string
    name = fields.Char(
        string='Transaction Name',
        required=True,
        default=lambda self: self._get_default_name(),
        copy=False,
    )
    date = fields.Date(string='Transaction Date', default=fields.Date.context_today, required=True)

    @api.model
    def _get_default_name(self):
        return self.env['ir.sequence'].next_by_code('finance.transaction') or 'New'
    amount = fields.Float(string='Amount', required=True)
    vat_amount = fields.Float(string='VAT Amount', default=0.0)
    transaction_type = fields.Selection([
        ('income', 'Income'),
        ('expense', 'Expense'),
    ], string='Type', required=True)
    notes = fields.Text(string='Notes')
    partner_id = fields.Many2one('res.partner', string='Partner')
    pos_order_id = fields.Many2one('pos.order', string='POS Order')
    stock_move_id = fields.Many2one('stock.move', string='Stock Move')
    report_id = fields.Many2one('finance.report', string='Report')
