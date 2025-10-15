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

        # Attempt to locate VAT accounts from the localization module
        vat_collected = env.ref('l10n_fj_minicoa.fj_21310', raise_if_not_found=False)
        vat_paid = env.ref('l10n_fj_minicoa.fj_21330', raise_if_not_found=False)

        for spec in specs:
            tax = Tax.search([
                ('name', '=', spec['name']),
                ('company_id', '=', company.id),
            ], limit=1)
            if not tax:
                tax = Tax.create({
                    'name': spec['name'],
                    'type_tax_use': spec['type_tax_use'],
                    'amount_type': 'percent',
                    'amount': spec['amount'],
                    'tax_group_id': group.id,
                    'company_id': company.id,
                    'active': True,
                    'price_include': False,
                })
            # Ensure tax repartition lines have accounts
            wanted_account = vat_collected if spec['type_tax_use'] == 'sale' else vat_paid
            if wanted_account:
                # set account on all tax repartition lines (invoice and refund)
                (tax.invoice_repartition_line_ids | tax.refund_repartition_line_ids).filtered(
                    lambda l: l.repartition_type == 'tax'
                ).write({'account_id': wanted_account.id})

        # ------------------------------
        # Ensure key control + COGS accounts
        # ------------------------------
        def ensure_account(code, name, account_type, reconcile=False):
            acc = env['account.account'].search([
                ('code', '=', code), ('company_id', '=', company.id)
            ], limit=1)
            if not acc:
                acc = env['account.account'].create({
                    'code': code,
                    'name': name,
                    'account_type': account_type,
                    'company_id': company.id,
                    'reconcile': reconcile,
                })
            return acc

        cogs_acc = env.ref('l10n_fj_minicoa.fj_51000', raise_if_not_found=False) or ensure_account('51000', 'Cost of Goods Sold', 'expense')
        pos_cash_ctrl = env.ref('l10n_fj_minicoa.fj_70100', raise_if_not_found=False) or ensure_account('70100', 'POS Cash Control', 'asset_current')
        pos_card_ctrl = env.ref('l10n_fj_minicoa.fj_70200', raise_if_not_found=False) or ensure_account('70200', 'POS Card Control', 'asset_current')

        # Set default on product categories where missing
        ProductCategory = env['product.category']
        missing_expense = ProductCategory.search([('company_id', '=', company.id), ('property_account_expense_categ_id', '=', False)])
        if cogs_acc and missing_expense:
            missing_expense.write({'property_account_expense_categ_id': cogs_acc.id})

        # Map POS payment methods to control accounts
        PaymentMethod = env['pos.payment.method']
        for pm in PaymentMethod.search([('company_id', '=', company.id)]):
            journal = pm.journal_id
            if not journal:
                continue
            if journal.type == 'cash' and pos_cash_ctrl and journal.default_account_id != pos_cash_ctrl:
                journal.default_account_id = pos_cash_ctrl.id
            if journal.type == 'bank' and pos_card_ctrl and pm.outstanding_account_id != pos_card_ctrl:
                pm.outstanding_account_id = pos_card_ctrl.id

        # ------------------------------
        # Create Sales-by-Category accounts and categories
        # ------------------------------
        sales_accounts_specs = [
            ('40100', 'Sales – Beverages'),
            ('40200', 'Sales – Snacks & Confectionery'),
            ('40300', 'Sales – Produce'),
            ('40400', 'Sales – Frozen Food'),
            ('40500', 'Sales – Household & Cleaning'),
            ('40900', 'Sales – Other'),
        ]
        sales_accounts = {}
        for code, name in sales_accounts_specs:
            acc = ensure_account(code, name, 'income')
            sales_accounts[code] = acc

        # Resolve stock accounts per company
        def by_code(code):
            return env['account.account'].search([('code', '=', code), ('company_id', '=', company.id)], limit=1)

        stock_val = by_code('12000') or env.ref('l10n_fj_minicoa.stock_valuation', raise_if_not_found=False)
        stock_in = by_code('12100') or env.ref('l10n_fj_minicoa.stock_in', raise_if_not_found=False)
        stock_out = by_code('12101') or env.ref('l10n_fj_minicoa.stock_out', raise_if_not_found=False)

        # Create/update categories with detailed per-department mapping
        ProductCategory = env['product.category']
        # Ensure root "Supermarket"
        root = env.ref('frcs_inventory.frcs_categ_root', raise_if_not_found=False) or ProductCategory.search([('name','=','Supermarket')], limit=1)
        if not root:
            root = ProductCategory.create({'name':'Supermarket', 'parent_id': env.ref('product.product_category_all').id})

        income_map = {
            'Beverages':'40100','Snacks':'40200','Fresh Produce':'40300','Frozen Foods':'40400',
            'Household':'40500','Others':'40900','Dairy':'40110','Meat':'40130','Vegetables':'40140',
            'Fruits':'40150','Bakery':'40160','Toiletries':'40510','Health & Beauty':'40520',
            'Baby Products':'40530','Cleaning Supplies':'40540',
        }
        cogs_map = {
            'Beverages':'51100','Snacks':'51200','Fresh Produce':'51300','Frozen Foods':'51400',
            'Household':'51500','Others':'51900','Dairy':'51110','Meat':'51130','Vegetables':'51140',
            'Fruits':'51150','Bakery':'51160','Toiletries':'51510','Health & Beauty':'51520',
            'Baby Products':'51530','Cleaning Supplies':'51540',
        }
        inv_map = {
            'Beverages':'12010','Snacks':'12020','Fresh Produce':'12030','Frozen Foods':'12070',
            'Household':'12080','Others':'12090','Dairy':'12011','Meat':'12031','Vegetables':'12041',
            'Fruits':'12051','Bakery':'12061','Toiletries':'12081','Health & Beauty':'12082',
            'Baby Products':'12083','Cleaning Supplies':'12084',
        }
        for name, inc_code in income_map.items():
            cogs_code = cogs_map.get(name)
            inv_code = inv_map.get(name)
            cat = ProductCategory.search([('name','=',name)], limit=1)
            if not cat:
                cat = ProductCategory.create({'name': name, 'parent_id': root.id})
            vals = {}
            inc = by_code(inc_code)
            if inc: vals['property_account_income_categ_id'] = inc.id
            if cogs_code:
                cgs = by_code(cogs_code)
                if cgs: vals['property_account_expense_categ_id'] = cgs.id
            if inv_code:
                inv = by_code(inv_code)
                if inv: vals['property_stock_valuation_account_id'] = inv.id
            if stock_in: vals['property_stock_account_input_categ_id'] = stock_in.id
            if stock_out: vals['property_stock_account_output_categ_id'] = stock_out.id
            if vals:
                cat.write(vals)
