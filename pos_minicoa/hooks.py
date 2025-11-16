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


def post_init_setup(env_or_cr, registry=None):
    """Executed after installation: make sure PoS configs include the Fiji payment methods."""
    cr = getattr(env_or_cr, 'cr', env_or_cr)
    env = api.Environment(cr, SUPERUSER_ID, {})
    Company = env['res.company']
    companies = Company.search([])
    print(f"[pos_minicoa] Post-init: linking Fiji PoS methods for {len(companies)} company(ies)")

    for company in companies:
        if company.country_id.code != 'FJ':
            continue
        payment_methods = env['pos.payment.method'].with_context(active_test=False).search([
            ('company_id', '=', company.id),
            ('name', 'in', ['POS Cash', 'POS Card', 'POS Mobile Money']),
        ])
        if not payment_methods:
            print(f"[pos_minicoa] {company.name}: no Fiji PoS payment methods found; nothing to link.")
            continue
        with env.cr.savepoint():
            try:
                _link_methods_to_all_configs(env, company, payment_methods)
                print(f"[pos_minicoa] {company.name}: PoS methods linked to each configuration.")
            except Exception as e:
                print(f"[pos_minicoa] {company.name}: error while ensuring methods -> {e}")
    return True
