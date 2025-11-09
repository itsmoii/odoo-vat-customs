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
        Account = self.env['account.account']
        domain = [('account_type', '=', 'asset_cash')]
        if 'company_id' in Account._fields:
            domain.insert(0, ('company_id', '=', company.id))
        liquidity = Account.search(domain, limit=1)

        for j in journals_data:
            Journal = self.env['account.journal']
            j_domain = [('code', '=', j['code'])]
            if 'company_id' in Journal._fields:
                j_domain.append(('company_id', '=', company.id))
            existing = Journal.search(j_domain, limit=1)

            vals = {
                'name': j['name'],
                'type': j['type'],
                'show_on_dashboard': True,
            }

            if j['type'] in ('cash', 'bank') and liquidity:
                vals['default_account_id'] = liquidity.id

            if not existing:
                create_vals = {**vals, 'code': j['code']}
                if 'company_id' in Journal._fields:
                    create_vals['company_id'] = company.id
                Journal.create(create_vals)
            else:
                existing.write(vals)
