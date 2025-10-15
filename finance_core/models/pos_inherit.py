from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError, AccessError
import decimal

class PosOrderInherit(models.Model):
    _inherit = 'pos.order'

    finance_transaction_count = fields.Integer(
        string='Finance Transactions', compute='_compute_finance_transaction_count'
    )

    def _compute_finance_transaction_count(self):
        # read_group returns a plain list of dicts, not a recordset, so
        # we cannot use mapped() here. Build the dict explicitly.
        groups = self.env['finance.transaction'].read_group(
            [('pos_order_id', 'in', self.ids)], ['pos_order_id'], ['pos_order_id']
        )
        counts = {
            # each row has format {'pos_order_id': (id, name), 'pos_order_id_count': n}
            row['pos_order_id'][0]: row['pos_order_id_count']
            for row in groups
            if row.get('pos_order_id')
        }
        for order in self:
            order.finance_transaction_count = counts.get(order.id, 0)

    def create_finance_transaction(self, name, amount, transaction_type):
        self.ensure_one()
        # Input validation
        if not isinstance(name, str):
            raise UserError("Transaction name must be a string")
        if not name.strip():
            raise UserError("Transaction name is required")
        if amount is None:
            raise UserError("Amount is required")
        if not isinstance(amount, (int, float, decimal.Decimal)):
            raise UserError("Amount must be a number")
        if isinstance(amount, float) and (amount != amount):  # Check for NaN
            raise UserError("Amount cannot be NaN")
        if transaction_type not in ['income', 'expense']:
            raise UserError("Transaction type must be 'income' or 'expense'")
        
        try:
            finance_transaction = self.env['finance.transaction'].create({
                'name': name,
                'amount': float(amount),
                'transaction_type': transaction_type,
                'pos_order_id': self.id,
                'partner_id': self.partner_id.id if self.partner_id else False,
                'date': fields.Date.to_date(self.date_order) if getattr(self, 'date_order', False) else fields.Date.context_today(self),
                'vat_amount': float(self.amount_tax or 0.0) if hasattr(self, 'amount_tax') else 0.0,
            })
            return finance_transaction
        except (ValidationError, AccessError) as error:
            raise UserError(f"Failed to create finance transaction: {error}")

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        for order in self:
            # Avoid duplicate entries
            existing = self.env['finance.transaction'].sudo().search_count([('pos_order_id', '=', order.id)])
            if existing:
                continue
            # Determine type and amount
            amt = float(order.amount_total or 0.0)
            tx_type = 'income' if amt >= 0 else 'expense'
            try:
                order.create_finance_transaction(
                    name=f"POS {order.name or 'Order'}",
                    amount=abs(amt),
                    transaction_type=tx_type,
                )
            except UserError:
                # Already validated inputs; skip if any minor issue
                continue
        return res

    def action_open_finance_transactions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Finance Transactions',
            'res_model': 'finance.transaction',
            'view_mode': 'list,form',
            'domain': [('pos_order_id', '=', self.id)],
            'context': {'default_pos_order_id': self.id, 'search_default_groupby_date': 1},
        }
