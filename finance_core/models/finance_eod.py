from odoo import models, fields, api


class FinanceEODService(models.TransientModel):
    _name = 'finance.eod.service'
    _description = 'Finance End of Day Posting Service'

    def _get_config(self):
        ICP = self.env['ir.config_parameter'].sudo()
        return {
            'journal_id': int(ICP.get_param('finance_core.pos_eod_journal_id') or 0) or False,
            'revenue_account_id': int(ICP.get_param('finance_core.pos_revenue_account_id') or 0) or False,
            'vat_account_id': int(ICP.get_param('finance_core.pos_vat_account_id') or 0) or False,
            'clearing_account_id': int(ICP.get_param('finance_core.pos_clearing_account_id') or 0) or False,
        }

    @api.model
    def post_eod_for_date(self, target_date=False):
        date_val = target_date or fields.Date.context_today(self)
        cfg = self._get_config()
        if not all([cfg['journal_id'], cfg['revenue_account_id'], cfg['vat_account_id'], cfg['clearing_account_id']]):
            return False

        Tx = self.env['finance.transaction']
        rg = Tx.read_group([
            ('transaction_type', '=', 'income'), ('date', '=', date_val)
        ], ['amount:sum', 'vat_amount:sum'], [])
        if not rg:
            return False
        sales = rg[0].get('amount_sum', 0.0) - rg[0].get('vat_amount_sum', 0.0)
        vat = rg[0].get('vat_amount_sum', 0.0)
        total = sales + vat

        Move = self.env['account.move']
        line_ids = [
            (0, 0, {'account_id': cfg['revenue_account_id'], 'credit': sales, 'debit': 0.0, 'name': f'EOD Sales {date_val}'}),
            (0, 0, {'account_id': cfg['vat_account_id'], 'credit': vat, 'debit': 0.0, 'name': f'EOD VAT {date_val}'}),
            (0, 0, {'account_id': cfg['clearing_account_id'], 'debit': total, 'credit': 0.0, 'name': f'EOD Clearing {date_val}'}),
        ]
        move = Move.create({
            'journal_id': cfg['journal_id'],
            'date': date_val,
            'ref': f'POS EOD {date_val}',
            'line_ids': line_ids,
        })
        move.action_post()
        return move.id

    @api.model
    def cron_post_yesterday(self):
        # Post EOD for yesterday
        yesterday = fields.Date.to_date(fields.Date.context_today(self)) - fields.Date.delta(days=1)
        self.post_eod_for_date(yesterday)

