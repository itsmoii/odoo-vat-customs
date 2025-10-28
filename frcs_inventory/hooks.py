from odoo import api, SUPERUSER_ID
from .fix_company_alignment import align_tax_companies


def post_init_hook(env):
    """
    Ensure FRCS VAT tax group and taxes exist for the installing company,
    align VAT tax line accounts, and repair mismatches without cross-company writes.
    """

    company = env.company
    for company in [company]:
        # Company-scoped env and models
        local_env = env.with_context(allowed_company_ids=[company.id]).with_company(company)
        Tax = local_env['account.tax']
        TaxGroup = local_env['account.tax.group']
        # Ensure a tax group per company
        tg_domain = [('name', '=', 'FRCS VAT')]
        if 'company_id' in TaxGroup._fields:
            tg_domain.append(('company_id', '=', company.id))
        group = TaxGroup.search(tg_domain, limit=1)
        if not group:
            vals = {'name': 'FRCS VAT'}
            if 'company_id' in TaxGroup._fields:
                vals['company_id'] = company.id
            group = TaxGroup.create(vals)

        # Ensure FRCS VAT taxes exist per company; create when missing
        specs = [
            {'label': '0% (Sales)', 'type_tax_use': 'sale', 'amount': 0.0},
            {'label': '12.5% (Sales)', 'type_tax_use': 'sale', 'amount': 12.5},
            {'label': '15% (Sales)', 'type_tax_use': 'sale', 'amount': 15.0},
            {'label': '9% (Sales)', 'type_tax_use': 'sale', 'amount': 9.0},
            {'label': '0% (Purchase)', 'type_tax_use': 'purchase', 'amount': 0.0},
            {'label': '12.5% (Purchase)', 'type_tax_use': 'purchase', 'amount': 12.5},
            {'label': '15% (Purchase)', 'type_tax_use': 'purchase', 'amount': 15.0},
            {'label': '9% (Purchase)', 'type_tax_use': 'purchase', 'amount': 9.0},
        ]

        # Resolve VAT accounts by code within the loop company to avoid cross-company writes
        def _vat_account(code):
            Account = local_env['account.account']
            domain = [('code', '=', code)]
            if 'company_id' in Account._fields:
                domain.append(('company_id', '=', company.id))
            return Account.search(domain, limit=1)

        vat_collected = _vat_account('21310')
        vat_paid = _vat_account('21330')

        for spec in specs:
            # Prefer existing taxes by rate + type; allow any name
            t_domain = [
                ('type_tax_use', '=', spec['type_tax_use']),
                ('amount_type', '=', 'percent'),
                ('amount', '=', spec['amount']),
                ('active', '=', True),
            ]
            if 'company_id' in Tax._fields:
                t_domain.append(('company_id', '=', company.id))
            tax = Tax.search(t_domain, limit=1)
            if not tax:
                vals = {
                    'name': f"VAT {spec['amount']}% ({'Sales' if spec['type_tax_use']=='sale' else 'Purchase'})",
                    'type_tax_use': spec['type_tax_use'],
                    'amount_type': 'percent',
                    'amount': spec['amount'],
                    'company_id': company.id,
                    'tax_group_id': group.id if group else False,
                    'active': True,
                    'price_include': not (spec['amount'] == 12.5 and spec['type_tax_use'] == 'sale'),
                }
                tax = Tax.create(vals)

                # Ensure repartition lines exist: base 100 + tax 100
                def _ensure(lines, field):
                    base = lines.filtered(lambda l: l.repartition_type == 'base')
                    taxl = lines.filtered(lambda l: l.repartition_type == 'tax')
                    ops = []
                    if not base:
                        ops.append((0, 0, {'repartition_type': 'base', 'factor_percent': 100.0}))
                    if not taxl:
                        ops.append((0, 0, {'repartition_type': 'tax', 'factor_percent': 100.0}))
                    if ops:
                        tax.write({field: ops})

                _ensure(tax.invoice_repartition_line_ids, 'invoice_repartition_line_ids')
                _ensure(tax.refund_repartition_line_ids, 'refund_repartition_line_ids')
            # Ensure tax repartition lines have accounts
            wanted_account = vat_collected if spec['type_tax_use'] == 'sale' else vat_paid
            if tax and wanted_account and (not hasattr(wanted_account, 'company_id') or wanted_account.company_id.id == company.id):
                # set account on all tax repartition lines (invoice and refund)
                (tax.invoice_repartition_line_ids | tax.refund_repartition_line_ids).filtered(
                    lambda l: l.repartition_type == 'tax'
                ).write({'account_id': wanted_account.id})

        # ------------------------------
        # Ensure key control + COGS accounts
        # ------------------------------
        def ensure_account(code, name, account_type, reconcile=False):
            Account = env['account.account']
            a_domain = [('code', '=', code)]
            if 'company_id' in Account._fields:
                a_domain.append(('company_id', '=', company.id))
            acc = Account.search(a_domain, limit=1)
            if not acc:
                vals = {
                    'code': code,
                    'name': name,
                    'account_type': account_type,
                }
                if 'company_id' in Account._fields:
                    vals['company_id'] = company.id
                if 'reconcile' in Account._fields:
                    vals['reconcile'] = reconcile
                acc = Account.create(vals)
            return acc

        cogs_acc = env.ref('l10n_fj_minicoa.fj_51000', raise_if_not_found=False) or ensure_account('51000', 'Cost of Goods Sold', 'expense')
        pos_cash_ctrl = env.ref('l10n_fj_minicoa.fj_70100', raise_if_not_found=False) or ensure_account('70100', 'POS Cash Control', 'asset_current')
        pos_card_ctrl = env.ref('l10n_fj_minicoa.fj_70200', raise_if_not_found=False) or ensure_account('70200', 'POS Card Control', 'asset_current')

        # Set default on product categories where missing
        ProductCategory = env['product.category']
        pc_domain = [('property_account_expense_categ_id', '=', False)]
        if 'company_id' in ProductCategory._fields:
            pc_domain.insert(0, ('company_id', '=', company.id))
        missing_expense = ProductCategory.search(pc_domain)
        if cogs_acc and missing_expense:
            missing_expense.write({'property_account_expense_categ_id': cogs_acc.id})

        # Map POS payment methods to control accounts
        PaymentMethod = env['pos.payment.method']
        pm_domain = []
        if 'company_id' in PaymentMethod._fields:
            pm_domain.append(('company_id', '=', company.id))
        for pm in PaymentMethod.search(pm_domain):
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
            Account = env['account.account']
            a_domain = [('code', '=', code)]
            if 'company_id' in Account._fields:
                a_domain.append(('company_id', '=', company.id))
            return Account.search(a_domain, limit=1)

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

    # ------------------------------
    # Bind existing VAT 12.5% taxes to XML IDs (no creation)
    # ------------------------------
    try:
        # Bind XMLIDs and ensure symmetric repartition for the installing company only
        local_env = env.with_context(allowed_company_ids=[company.id]).with_company(company)
        Tax = local_env['account.tax']
        IMD = local_env['ir.model.data']

        def _bind_xmlid(module, name, model, rec):
            imd = IMD.search([('module', '=', module), ('name', '=', name), ('model', '=', model)], limit=1)
            if imd:
                if imd.res_id != rec.id:
                    imd.res_id = rec.id
            else:
                IMD.create({'module': module, 'name': name, 'model': model, 'res_id': rec.id, 'noupdate': True})

        sale_domain = [
            ('type_tax_use', '=', 'sale'),
            ('amount_type', '=', 'percent'),
            ('amount', '=', 12.5),
        ]
        if 'company_id' in Tax._fields:
            sale_domain.insert(0, ('company_id', '=', company.id))
        sale = Tax.search(sale_domain, order='id asc', limit=1)

        purch_domain = [
            ('type_tax_use', '=', 'purchase'),
            ('amount_type', '=', 'percent'),
            ('amount', '=', 12.5),
        ]
        if 'company_id' in Tax._fields:
            purch_domain.insert(0, ('company_id', '=', company.id))
        purch = Tax.search(purch_domain, order='id asc', limit=1)

        if sale:
            _bind_xmlid('frcs_inventory', 'vat_12_5_sale', 'account.tax', sale)
        if purch:
            _bind_xmlid('frcs_inventory', 'vat_12_5_purchase', 'account.tax', purch)

        # Ensure symmetric repartition and map VAT accounts on the 12.5% pair
        Account = local_env['account.account']
        d1 = [('code', '=', '21310')]
        d2 = [('code', '=', '21330')]
        if 'company_id' in Account._fields:
            d1.append(('company_id', '=', company.id))
            d2.append(('company_id', '=', company.id))
        acc21310 = Account.search(d1, limit=1)
        acc21330 = Account.search(d2, limit=1)

        for tax in (sale | purch):
            if not tax:
                continue
            def _ensure(lines, field):
                base = lines.filtered(lambda l: l.repartition_type == 'base')
                taxl = lines.filtered(lambda l: l.repartition_type == 'tax')
                ops = []
                if not base:
                    ops.append((0, 0, {'repartition_type': 'base', 'factor_percent': 100.0}))
                if not taxl:
                    ops.append((0, 0, {'repartition_type': 'tax', 'factor_percent': 100.0}))
                if ops:
                    tax.write({field: ops})

            _ensure(tax.invoice_repartition_line_ids, 'invoice_repartition_line_ids')
            _ensure(tax.refund_repartition_line_ids, 'refund_repartition_line_ids')

            acc = acc21310 if tax.type_tax_use == 'sale' else acc21330
            if acc:
                (tax.invoice_repartition_line_ids | tax.refund_repartition_line_ids).filtered(
                    lambda l: l.repartition_type == 'tax'
                ).write({'account_id': acc.id})
    except Exception:
        # Binding should never break install/upgrade
        pass

    # Final repair: drop cross-company account assignments on tax lines
    try:
        Line = env['account.tax.repartition.line']
        lines = Line.search([('account_id', '!=', False)])
        mismatched = lines.filtered(lambda l: hasattr(l, 'company_id') and l.account_id.company_id and l.company_id and l.account_id.company_id.id != l.company_id.id)
        if mismatched:
            mismatched.write({'account_id': False})
    except Exception:
        pass

    # Final alignment: ensure lines company matches tax company for Fiji VAT in env.company
    try:
        align_tax_companies(env, target_company=company)
    except Exception:
        # Never block install because of alignment heuristics
        pass
