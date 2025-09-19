from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    """
    Ensure FRCS VAT tax group and 0% / 12.5% taxes exist for every company.
    This avoids empty dropdowns in multi-company environments.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    Company = env['res.company']
    Tax = env['account.tax']
    TaxGroup = env['account.tax.group']

    for company in Company.search([]):
        # Ensure a tax group per company
        group = TaxGroup.search([
            ('name', '=', 'FRCS VAT'),
            ('company_id', '=', company.id),
        ], limit=1)
        if not group:
            group = TaxGroup.create({
                'name': 'FRCS VAT',
                'company_id': company.id,
            })

        # Ensure the four FRCS taxes per company
        specs = [
            {'name': 'FRCS VAT 0% (Sales)', 'type_tax_use': 'sale', 'amount': 0.0},
            {'name': 'FRCS VAT 12.5% (Sales)', 'type_tax_use': 'sale', 'amount': 12.5},
            {'name': 'FRCS VAT 0% (Purchase)', 'type_tax_use': 'purchase', 'amount': 0.0},
            {'name': 'FRCS VAT 12.5% (Purchase)', 'type_tax_use': 'purchase', 'amount': 12.5},
        ]

        for spec in specs:
            tax = Tax.search([
                ('name', '=', spec['name']),
                ('company_id', '=', company.id),
            ], limit=1)
            if not tax:
                Tax.create({
                    'name': spec['name'],
                    'type_tax_use': spec['type_tax_use'],
                    'amount_type': 'percent',
                    'amount': spec['amount'],
                    'tax_group_id': group.id,
                    'company_id': company.id,
                    'active': True,
                    'price_include': False,
                })

