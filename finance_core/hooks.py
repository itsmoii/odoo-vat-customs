from odoo import api, SUPERUSER_ID


def post_init_assign_taxes(cr, registry):
    """Post-init housekeeping for taxes.

    - Ensure products with no sales taxes get VAT 0% and VAT 12.5% (from l10n_fj_minicoa).
    - Archive duplicate finance_core taxes if they exist.
    - Keep only the 4 canonical sales taxes active.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Prefer l10n Fiji VAT taxes as canonical; fallback to finance_core if needed
    tax0 = env.ref("l10n_fj_minicoa.tax_vat_0_sale", raise_if_not_found=False) or \
           env.ref("finance_core.tax_vat_0", raise_if_not_found=False)
    tax125 = env.ref("l10n_fj_minicoa.tax_vat_125_sale", raise_if_not_found=False) or \
             env.ref("finance_core.tax_vat_125", raise_if_not_found=False)

    if tax0 and tax125:
        products = env["product.template"].search([("taxes_id", "=", False)])
        if products:
            products.write({"taxes_id": [(6, 0, [tax0.id, tax125.id])]})

    # Canonical set to keep (8 taxes: 4 rates × sale/purchase) -> l10n_fj_minicoa
    keep_xmlids = (
        "l10n_fj_minicoa.tax_vat_0_sale",
        "l10n_fj_minicoa.tax_vat_0_purchase",
        "l10n_fj_minicoa.tax_vat_9_sale",
        "l10n_fj_minicoa.tax_vat_9_purchase",
        "l10n_fj_minicoa.tax_vat_125_sale",
        "l10n_fj_minicoa.tax_vat_125_purchase",
        "l10n_fj_minicoa.tax_vat_15_sale",
        "l10n_fj_minicoa.tax_vat_15_purchase",
    )
    keep_ids = []
    for xid in keep_xmlids:
        rec = env.ref(xid, raise_if_not_found=False)
        if rec:
            keep_ids.append(rec.id)

    company = env.ref("base.main_company")
    Tax = env["account.tax"]

    # If the l10n taxes are installed, archive everything else
    if keep_ids:
        other_taxes = Tax.search([
            ("company_id", "=", company.id),
            ("type_tax_use", "in", ["sale", "purchase"]),
            ("id", "not in", keep_ids),
        ])
        if other_taxes:
            other_taxes.write({"active": False})

    # Archive finance_core duplicates if present
    fc_xids = (
        "finance_core.tax_vat_0",
        "finance_core.tax_vat_125",
        "finance_core.tax_vat_9",
        "finance_core.tax_vat_15",
    )
    fc_ids = []
    for xid in fc_xids:
        rec = env.ref(xid, raise_if_not_found=False)
        if rec:
            fc_ids.append(rec.id)
    if fc_ids:
        Tax.browse(fc_ids).write({"active": False})


def post_load_cleanup(cr, registry):
    """Run at server load/upgrade: archive duplicate finance_core taxes and keep only canonical 4.

    This ensures upgrades also clean up previously created duplicates.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    Tax = env['account.tax']
    # Archive finance_core duplicates
    fc_xids = (
        'finance_core.tax_vat_0',
        'finance_core.tax_vat_125',
        'finance_core.tax_vat_9',
        'finance_core.tax_vat_15',
    )
    fc_ids = []
    for xid in fc_xids:
        rec = env.ref(xid, raise_if_not_found=False)
        if rec:
            fc_ids.append(rec.id)
    if fc_ids:
        Tax.browse(fc_ids).write({'active': False})

    # Keep only canonical 8 if they exist (l10n)
    keep_xmlids = (
        'l10n_fj_minicoa.tax_vat_0_sale',
        'l10n_fj_minicoa.tax_vat_0_purchase',
        'l10n_fj_minicoa.tax_vat_9_sale',
        'l10n_fj_minicoa.tax_vat_9_purchase',
        'l10n_fj_minicoa.tax_vat_125_sale',
        'l10n_fj_minicoa.tax_vat_125_purchase',
        'l10n_fj_minicoa.tax_vat_15_sale',
        'l10n_fj_minicoa.tax_vat_15_purchase',
    )
    keep_ids = []
    for xid in keep_xmlids:
        rec = env.ref(xid, raise_if_not_found=False)
        if rec:
            keep_ids.append(rec.id)
    if keep_ids:
        company = env.ref('base.main_company')
        other = Tax.search([
            ('company_id', '=', company.id),
            ('type_tax_use', 'in', ['sale', 'purchase']),
            ('id', 'not in', keep_ids),
        ])
        if other:
            other.write({'active': False})
        # Ensure canonical are active
        Tax.browse(keep_ids).write({'active': True})
