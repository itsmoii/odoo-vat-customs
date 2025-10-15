from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    """
    After installation/upgrade, ensure each POS uses cash-only payment methods.
    - Keep only methods with is_cash_count = True on every pos.config
    - If no cash method exists for a company, try to create defaults via
      pos.config helper and then keep the cash one only.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    PosConfig = env['pos.config']
    PaymentMethod = env['pos.payment.method']

    for config in PosConfig.search([]):
        # Find any cash methods in the company
        cash_methods = PaymentMethod.search([
            ('company_id', '=', config.company_id.id),
            ('is_cash_count', '=', True),
        ])
        if not cash_methods:
            # Create default journals + payment methods and pick the cash ones
            try:
                _journals, pmethods = config._create_journal_and_payment_methods()
                cash_methods = PaymentMethod.browse(pmethods).filtered('is_cash_count')
            except Exception:
                cash_methods = PaymentMethod.search([
                    ('company_id', '=', config.company_id.id),
                    ('is_cash_count', '=', True),
                ])

        if cash_methods:
            config.write({'payment_method_ids': [(6, 0, cash_methods.ids)]})

