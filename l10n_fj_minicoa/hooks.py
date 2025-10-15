from odoo import api, SUPERUSER_ID


def post_init_setup(cr, registry):
    """
    Fiji bootstrap: ensure a CoA is installed, set company to Fiji + FJD,
    create/link FRCS VAT taxes, and attach POS payment methods.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    company = env.company

    # 1) Set company country to Fiji and currency to FJD if available
    try:
        fj = env['res.country'].search([('code', '=', 'FJ')], limit=1)
        if fj and not company.country_id:
            company.country_id = fj.id
    except Exception:
        pass

    try:
        fjd = env['res.currency'].search([('name', '=', 'FJD')], limit=1)
        if fjd:
            company.currency_id = fjd.id
    except Exception:
        pass

    # 2) Ensure a Chart of Accounts exists on the ROOT company first
    try:
        act = env['account.chart.template']
        root = company.root_id
        # Install our Fiji MiniCOA on root if nothing is installed yet
        if not root.chart_template:
            act.try_loading('fj_minicoa', root, install_demo=False)
        # For child companies, mark the selected template without duplicating accounts
        if company != root and not company.chart_template:
            company.chart_template = 'fj_minicoa'
    except Exception:
        # If already installed or in testing contexts, ignore
        pass

    # 3) Company default taxes from this module (if present)
    vat_125_sale = env.ref("l10n_fj_minicoa.tax_vat_125_sale", raise_if_not_found=False)
    vat_0_pur = env.ref("l10n_fj_minicoa.tax_vat_0_purchase", raise_if_not_found=False)
    # Prefer explicit FRCS labeled 15% if available
    vat_15_sale = env.ref("l10n_fj_minicoa.tax_frcs_vat_15_sales", raise_if_not_found=False)
    updates = {}
    if vat_15_sale:
        updates["account_sale_tax_id"] = vat_15_sale.id
    elif vat_125_sale:
        updates["account_sale_tax_id"] = vat_125_sale.id
    if vat_0_pur:
        updates["account_purchase_tax_id"] = vat_0_pur.id
    if updates:
        company.write(updates)

    # 4) Upsert POS journals and payment methods without hard-coded XML IDs
    Journal = env['account.journal']
    def _get_or_create(code, name, jtype):
        j = Journal.search([('code', '=', code), ('company_id', '=', company.id)], limit=1)
        if not j:
            j = Journal.create({'name': name, 'code': code, 'type': jtype, 'company_id': company.id})
        return j

    sale_journal = _get_or_create('POSS', 'POS Sales', 'sale')
    cash_journal = _get_or_create('POSC', 'POS Cash', 'cash')
    bank_journal = _get_or_create('POSB', 'POS Bank', 'bank')

    # Ensure liquidity account is set on cash/bank journals
    def _find_liquidity_account():
        return env['account.account'].search([
            ('account_type', '=', 'asset_cash'),
            ('company_id', '=', company.id),
        ], limit=1)

    liquidity = _find_liquidity_account()
    for j in (cash_journal, bank_journal):
        try:
            if j and not j.default_account_id and liquidity:
                j.default_account_id = liquidity.id
        except Exception:
            # If constraints or multi-company issues occur, skip silently
            pass

    # 4b) Ensure company default PoS receivable is set (used by POS closing entries)
    try:
        if not company.account_default_pos_receivable_account_id:
            pos_recv = env['account.account'].search([
                ('account_type', '=', 'asset_receivable'),
                ('reconcile', '=', True),
                ('deprecated', '=', False),
                ('company_id', '=', company.id),
            ], limit=1)
            if pos_recv:
                company.account_default_pos_receivable_account_id = pos_recv.id
    except Exception:
        pass

    PM = env['pos.payment.method']
    pm_cash = PM.search([('journal_id', '=', cash_journal.id), ('company_id', '=', company.id)], limit=1)
    if not pm_cash:
        pm_cash = PM.create({'name': 'Cash', 'journal_id': cash_journal.id, 'company_id': company.id})
    pm_bank = PM.search([('journal_id', '=', bank_journal.id), ('company_id', '=', company.id)], limit=1)
    if not pm_bank:
        pm_bank = PM.create({'name': 'Card/Bank', 'journal_id': bank_journal.id, 'company_id': company.id})

    pos_configs = env['pos.config'].search([])
    for cfg in pos_configs:
        new_set = (cfg.payment_method_ids | pm_cash | pm_bank)
        cfg.write({'payment_method_ids': [(6, 0, new_set.ids)]})

    # 5) Map VAT accounts on taxes for the current company (avoid XML company mismatch)
    def _acc_by_code(code):
        return env['account.account'].search([('code', '=', code), ('company_id', '=', company.id)], limit=1)

    vat_collected = _acc_by_code('21310')
    vat_paid = _acc_by_code('21330')
    if vat_collected or vat_paid:
        taxes = env['account.tax'].search([('company_id', '=', company.id), ('type_tax_use', 'in', ['sale', 'purchase'])])
        for tax in taxes:
            account = vat_collected if tax.type_tax_use == 'sale' else vat_paid
            if account:
                (tax.invoice_repartition_line_ids | tax.refund_repartition_line_ids).filtered(
                    lambda l: l.repartition_type == 'tax'
                ).write({'account_id': account.id})

    # 6) Assign FRCS labels based on amount for Fiji VAT taxes when missing
    label_map = {9.0: 'A', 0.0: 'B', 15.0: 'D', 12.5: 'G'}
    Tax = env['account.tax']
    frcs_group = env.ref('l10n_fj_minicoa.tax_group_vat', raise_if_not_found=False)
    for rate, label in label_map.items():
        domain = [('amount_type', '=', 'percent'), ('amount', '=', rate), ('active', '=', True)]
        if frcs_group:
            domain += [('tax_group_id', '=', frcs_group.id)]
        taxes = Tax.search(domain)
        for tx in taxes:
            if not getattr(tx, 'frcs_label', False):
                tx.frcs_label = label

def pre_init_cleanup(cr):
    """Before loading XML, rename legacy taxes defined by other modules that
    would clash on unique names (e.g., FRCS VAT 0% (Sales)). This frees names
    so our canonical l10n_fj_minicoa taxes can be created safely.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    imd = env['ir.model.data']
    # First, rename known legacy taxes created by our other modules
    legacy_ids = imd.search([
        ('module', 'in', ['frcs_inventory', 'pos_minicoa']),
        ('model', '=', 'account.tax'),
        ('name', 'in', ['tax_sale_frcs_0', 'tax_sale_frcs_125', 'tax_purchase_frcs_0', 'tax_purchase_frcs_125'])
    ])
    to_rename_set = {
        'FRCS VAT 0% (Sales)', 'FRCS VAT 12.5% (Sales)', 'FRCS VAT 15% (Sales)', 'FRCS VAT 9% (Sales)',
        'FRCS VAT 0% (Purchase)', 'FRCS VAT 12.5% (Purchase)'
    }
    for rec in legacy_ids:
        tax = env['account.tax'].browse(rec.res_id)
        if tax and tax.exists() and tax.name in to_rename_set and not tax.name.endswith('(legacy)'):
            tax.name = f"{tax.name} (legacy)"

    # Second, catch any manually created duplicates by name (no XMLID)
    # Do NOT rename our own canonical taxes if they already exist (with our XMLIDs)
    canonical_xmlids = {
        'tax_frcs_vat_0_sales', 'tax_frcs_vat_125_sales', 'tax_frcs_vat_15_sales', 'tax_frcs_vat_9_sales',
        'tax_vat_0_purchase', 'tax_vat_125_purchase',
    }
    # Map xmlid -> res_id for quick skip
    canonical_imd = imd.search([
        ('module', '=', 'l10n_fj_minicoa'),
        ('model', '=', 'account.tax'),
        ('name', 'in', list(canonical_xmlids))
    ])
    canonical_res_ids = set(canonical_imd.mapped('res_id'))

    existing = env['account.tax'].search([('name', 'in', list(to_rename_set))])
    for tx in existing:
        if tx.id in canonical_res_ids:
            continue
        if not tx.name.endswith('(legacy)'):
            tx.name = f"{tx.name} (legacy)"

    # 3) Ensure our canonical XMLID l10n_fj_minicoa.tax_group_vat points to an
    # existing FRCS VAT group (whichever is most used), so XML updates the
    # group instead of trying to create/replace and potentially unlink others.
    Group = env['account.tax.group']
    Tax = env['account.tax']
    groups = Group.search([('name', 'ilike', 'FRCS VAT')])
    chosen = False
    if groups:
        # Pick the group referenced by the most taxes
        counts = [(g, Tax.search_count([('tax_group_id', '=', g.id)])) for g in groups]
        counts.sort(key=lambda t: t[1], reverse=True)
        chosen = counts[0][0]
    if not chosen:
        # Fallback: try known XMLIDs from other modules
        for xml in ['frcs_inventory.tax_group_frcs_vat', 'pos_minicoa.frcs_vat_group']:
            g = env.ref(xml, raise_if_not_found=False)
            if g:
                chosen = g
                break
    if chosen:
        imd_rec = imd.search([
            ('module', '=', 'l10n_fj_minicoa'),
            ('name', '=', 'tax_group_vat'),
            ('model', '=', 'account.tax.group'),
        ], limit=1)
        if imd_rec:
            imd_rec.res_id = chosen.id
        else:
            imd.create({
                'module': 'l10n_fj_minicoa',
                'name': 'tax_group_vat',
                'model': 'account.tax.group',
                'res_id': chosen.id,
                'noupdate': True,
            })
