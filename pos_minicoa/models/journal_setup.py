from odoo import api, models, fields


class POSJournalSetup(models.TransientModel):
    _name = 'pos.journal.setup'
    _description = 'Auto create or update POS journals safely'

    @api.model
    def create_pos_journals(self):
        """Create POS journals only if they don't already exist (idempotent)."""
        company = self.env.company

        journals_data = [
            {
                'name': 'POS Sales',
                'code': 'POSS',
                'type': 'sale',
            },
            {
                'name': 'POS Bank',
                'code': 'POSB',
                'type': 'bank',
            },
            {
                'name': 'POS Cash',
                'code': 'POSC',
                'type': 'cash',
            },
        ]

        # Find a liquidity account to plug on cash/bank journals when missing
        liquidity = self.env['account.account'].search([
            ('company_id', '=', company.id),
            ('account_type', '=', 'asset_cash'),
        ], limit=1)

        for j in journals_data:
            Journal = self.env['account.journal']
            existing = Journal.search([
                ('code', '=', j['code']),
                ('company_id', '=', company.id),
            ], limit=1)

            vals = {
                'name': j['name'],
                'type': j['type'],
                'show_on_dashboard': True,
            }

            if j['type'] in ('cash', 'bank') and liquidity:
                vals['default_account_id'] = liquidity.id

            if not existing:
                Journal.create({
                    **vals,
                    'code': j['code'],
                    'company_id': company.id,
                })
            else:
                existing.write(vals)

