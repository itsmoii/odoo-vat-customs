from odoo import models, fields, api

class FinanceReport(models.Model):
    _name = 'finance.report'
    _description = 'Finance Report'
    _order = 'date desc'

    name = fields.Char(string='Report Name', required=True)
    date = fields.Date(string='Report Date', default=fields.Date.context_today, required=True)
    total_amount = fields.Float(string='Total Amount', compute='_compute_total_amount', store=True)
    details = fields.Text(string='Details')
    transaction_ids = fields.One2many('finance.transaction', 'report_id', string='Transactions')

    @api.depends('transaction_ids.amount')
    def _compute_total_amount(self):
        if not self:
            return

        # read_group returns alias 'amount_sum' for 'amount:sum'
        result = self.env['finance.transaction'].read_group(
            [('report_id', 'in', self.ids)],
            ['amount:sum'],
            ['report_id']
        )

        amounts = {r['report_id'][0]: r.get('amount_sum', 0.0) for r in result}
        for report in self:
            report.total_amount = amounts.get(report.id, 0.0)
