"""POS MiniCOA hooks with version-robust domains.

This module avoids hard-coding fields that may differ across Odoo versions
(e.g., account.account.company_id or deprecated vs active) by checking model
_fields at runtime.
"""

from odoo import api, SUPERUSER_ID


def pre_init_attach_journals(cr):
    """No-op pre-init hook."""
    print("[pos_minicoa] Pre-init skipped: no environment created.")
    return True


def _ensure_liquidity_account(env, company):
    Account = env['account.account']
    domain = [('account_type', 'in', ['asset_cash'])]
    if 'deprecated' in Account._fields:
        domain.append(('deprecated', '=', False))
    elif 'active' in Account._fields:
        domain.append(('active', '=', True))
    if 'company_id' in Account._fields:
        domain.append(('company_id', '=', company.id))
    acc = Account.search(domain, limit=1)
    if not acc:
        fallback = [('account_type', '=', 'asset_receivable')]
        if 'reconcile' in Account._fields:
            fallback.append(('reconcile', '=', True))
        if 'deprecated' in Account._fields:
            fallback.append(('deprecated', '=', False))
        elif 'active' in Account._fields:
            fallback.append(('active', '=', True))
        if 'company_id' in Account._fields:
            fallback.append(('company_id', '=', company.id))
        acc = Account.search(fallback, limit=1)
    return acc


def _ensure_receivable_account(env, company):
    acc = getattr(company, 'account_default_pos_receivable_account_id', False)
    if acc:
        return acc
    Account = env['account.account']
    domain = [('account_type', '=', 'asset_receivable')]
    if 'reconcile' in Account._fields:
        domain.append(('reconcile', '=', True))
    if 'deprecated' in Account._fields:
        domain.append(('deprecated', '=', False))
    elif 'active' in Account._fields:
        domain.append(('active', '=', True))
    if 'company_id' in Account._fields:
        domain.append(('company_id', '=', company.id))
    return Account.search(domain, limit=1)


def _ensure_bank_journal(env, company, name, code):
    Journal = env['account.journal']
    j_domain = [('name', '=', name)]
    if 'company_id' in Journal._fields:
        j_domain.append(('company_id', '=', company.id))
    journal = Journal.search(j_domain, limit=1)
    if journal:
        return journal

    liquidity = _ensure_liquidity_account(env, company)
    vals = {
        'name': name,
        'type': 'bank',
        'code': code,
    }
    if 'company_id' in Journal._fields:
        vals['company_id'] = company.id
    if 'default_account_id' in Journal._fields and liquidity:
        vals['default_account_id'] = liquidity.id
    return Journal.create(vals)


def _ensure_pos_method(env, company, name, journal, outstanding=None):
    PM = env['pos.payment.method']
    pm_domain = [('name', '=', name)]
    if 'company_id' in PM._fields:
        pm_domain.append(('company_id', '=', company.id))
    pm = PM.search(pm_domain, limit=1)
    if pm:
        updates = {}
        if pm.journal_id.id != journal.id:
            updates['journal_id'] = journal.id
        if outstanding and 'outstanding_account_id' in PM._fields:
            if (not pm.outstanding_account_id) or (pm.outstanding_account_id.id != outstanding.id):
                updates['outstanding_account_id'] = outstanding.id
        if updates:
            pm.write(updates)
        return pm

    vals = {
        'name': name,
        'journal_id': journal.id,
        'payment_method_type': 'none',
    }
    if 'company_id' in PM._fields:
        vals['company_id'] = company.id
    if 'outstanding_account_id' in PM._fields and outstanding:
        vals['outstanding_account_id'] = outstanding.id
    return PM.create(vals)


def _link_methods_to_all_configs(env, company, methods):
    Config = env['pos.config']
    cfg_domain = []
    if 'company_id' in Config._fields:
        cfg_domain.append(('company_id', '=', company.id))
    configs = Config.search(cfg_domain)
    for cfg in configs:
        cmds = []
        for pm in methods:
            if pm not in cfg.payment_method_ids:
                cmds.append((4, pm.id))
        if cmds:
            cfg.write({'payment_method_ids': cmds})


def post_init_setup(env):
    """Executed after installation: ensure Card/mPaisa methods and link to POS configs across companies."""
    Company = env['res.company']
    companies = Company.search([])
    print(f"[pos_minicoa] Post-init: ensuring Card/mPaisa for {len(companies)} company(ies)")

    for company in companies:
        with env.cr.savepoint():
            try:
                receivable = _ensure_receivable_account(env, company)
                if not receivable:
                    print(f"[pos_minicoa] {company.name}: no receivable account found; skipping.")
                    continue

                card_journal = _ensure_bank_journal(env, company, 'Card', 'CARD')
                mpaisa_journal = _ensure_bank_journal(env, company, 'M-Paisa', 'MPAI')

                card_pm = _ensure_pos_method(env, company, 'Card', card_journal, outstanding=receivable)
                mpaisa_pm = _ensure_pos_method(env, company, 'M-Paisa', mpaisa_journal, outstanding=receivable)

                _link_methods_to_all_configs(env, company, [card_pm, mpaisa_pm])
                print(f"[pos_minicoa] {company.name}: Card/mPaisa ensured and linked.")
            except Exception as e:
                print(f"[pos_minicoa] {company.name}: error while ensuring methods -> {e}")
    return True
