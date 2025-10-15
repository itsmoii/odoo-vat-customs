# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def pre_init_attach_journals(cr):
    """
    Pre-init hook disabled.
    Runs before the ORM environment is ready, so we don't build an Environment here.
    """
    print("· Pre-init skipped: no environment created.")
    return True


def _ensure_liquidity_account(env, company):
    Account = env['account.account']
    acc = Account.search([
        ('company_id', '=', company.id),
        ('account_type', 'in', ['asset_cash']),
        ('deprecated', '=', False),
    ], limit=1)
    if not acc:
        acc = Account.search([
            ('company_id', '=', company.id),
            ('account_type', '=', 'asset_receivable'),
            ('reconcile', '=', True),
            ('deprecated', '=', False),
        ], limit=1)
    return acc


def _ensure_receivable_account(env, company):
    acc = getattr(company, 'account_default_pos_receivable_account_id', False)
    if acc:
        return acc
    return env['account.account'].search([
        ('company_id', '=', company.id),
        ('account_type', '=', 'asset_receivable'),
        ('reconcile', '=', True),
        ('deprecated', '=', False),
    ], limit=1)


def _ensure_bank_journal(env, company, name, code):
    Journal = env['account.journal']
    journal = Journal.search([
        ('name', '=', name),
        ('company_id', '=', company.id),
    ], limit=1)
    if journal:
        return journal

    liquidity = _ensure_liquidity_account(env, company)
    vals = {
        'name': name,
        'type': 'bank',
        'code': code,
        'company_id': company.id,
    }
    if 'default_account_id' in env['account.journal']._fields and liquidity:
        vals['default_account_id'] = liquidity.id
    return Journal.create(vals)


def _ensure_pos_method(env, company, name, journal, outstanding=None):
    PM = env['pos.payment.method']
    pm = PM.search([
        ('name', '=', name),
        ('company_id', '=', company.id),
    ], limit=1)
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
        'company_id': company.id,
        'payment_method_type': 'none',
    }
    if 'outstanding_account_id' in PM._fields and outstanding:
        vals['outstanding_account_id'] = outstanding.id
    return PM.create(vals)


def _link_methods_to_all_configs(env, company, methods):
    Config = env['pos.config']
    configs = Config.search([('company_id', '=', company.id)])
    for cfg in configs:
        cmds = []
        for pm in methods:
            if pm not in cfg.payment_method_ids:
                cmds.append((4, pm.id))
        if cmds:
            cfg.write({'payment_method_ids': cmds})


def post_init_setup(env):
    """Executed automatically after module installation: ensure Card/mPaisa payment methods and link to POS configs for ALL companies."""
    Company = env['res.company']
    companies = Company.search([])
    print(f"· Post-init: ensuring Card/mPaisa for {len(companies)} companie(s)…")

    for company in companies:
        with env.cr.savepoint():
            try:
                receivable = _ensure_receivable_account(env, company)
                if not receivable:
                    print(f"! {company.name}: no receivable account found; skipping.")
                    continue

                card_journal = _ensure_bank_journal(env, company, 'Card', 'CARD')
                mpaisa_journal = _ensure_bank_journal(env, company, 'M-Paisa', 'MPAI')

                card_pm = _ensure_pos_method(env, company, 'Card', card_journal, outstanding=receivable)
                mpaisa_pm = _ensure_pos_method(env, company, 'M-Paisa', mpaisa_journal, outstanding=receivable)

                _link_methods_to_all_configs(env, company, [card_pm, mpaisa_pm])
                print(f"✓ {company.name}: Card/mPaisa ensured and linked.")
            except Exception as e:
                print(f"! {company.name}: error while ensuring methods -> {e}")
    return True
