from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)

def pre_init_cleanup(cr):
    """Run before XML data loads — removes any leftover duplicates early."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    Tax = env['account.tax']
    Company = env['res.company']

    _logger.info("🧹 Pre-init: Cleaning duplicate Fiji taxes...")

    # Remove all taxes belonging to 'My Company' if it exists
    my_company = Company.search([('name', '=', 'My Company')], limit=1)
    if my_company:
        my_taxes = Tax.search([('company_id', '=', my_company.id)])
        if my_taxes:
            _logger.info("🗑 Removing %s taxes from My Company before install", len(my_taxes))
            try:
                my_taxes.write({'active': False})
            except Exception:
                my_taxes.write({'active': False})
        env.cr.commit()

    # Archive obvious duplicate Fiji VAT rates
    for rate in (0.0, 9.0, 12.5, 15.0):
        taxes = Tax.search([
            ('amount', '=', rate),
            ('country_id.code', '=', 'FJ'),
            ('active', '=', True),
        ], order='id asc')
        if len(taxes) > 2:
            extras = taxes[2:]
            extras.write({'active': False})
            _logger.info(" Archived %s duplicate VAT %.1f%% taxes", len(extras), rate)


def post_init_setup(cr, registry):
    """Main Fiji setup — runs after module install or update."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    company = env.company

    _logger.info("🇫🇯 Running Fiji post-install setup...")

    # Country / currency setup
    fj = env['res.country'].search([('code', '=', 'FJ')], limit=1)
    if fj and not company.country_id:
        company.country_id = fj.id
    fjd = env['res.currency'].search([('name', '=', 'FJD')], limit=1)
    if fjd:
        company.currency_id = fjd.id

    # Chart of Accounts
    try:
        act = env['account.chart.template']
        root = company.root_id
        if not root.chart_template:
            act.try_loading('fj_minicoa', root, install_demo=False)
        if company != root and not company.chart_template:
            company.chart_template = 'fj_minicoa'
    except Exception:
        pass

    # Default taxes from chart templates (CSV ids)
    vat_125_sale = env.ref("l10n_fj_minicoa.fj_tax_sale_125", raise_if_not_found=False)
    vat_0_pur = env.ref("l10n_fj_minicoa.fj_tax_purchase_0", raise_if_not_found=False)
    if vat_125_sale and vat_0_pur:
        company.write({
            "account_sale_tax_id": vat_125_sale.id,
            "account_purchase_tax_id": vat_0_pur.id
        })

    # Ensure the four FRCS VAT rates exist (0, 9, 12.5, 15) for both sale and purchase
    Tax = env['account.tax']
    group = env.ref('l10n_fj_minicoa.tax_group_vat', raise_if_not_found=False)
    acc_collected = env.ref('l10n_fj_minicoa.fj_21310', raise_if_not_found=False)
    acc_paid = env.ref('l10n_fj_minicoa.fj_21330', raise_if_not_found=False)
    for rate in (0.0, 9.0, 12.5, 15.0):
        for use in ('sale', 'purchase'):
            existing = Tax.search([
                ('company_id', '=', company.id),
                ('type_tax_use', '=', use),
                ('amount_type', '=', 'percent'),
                ('amount', '=', rate),
            ], limit=1)
            if existing:
                continue
            vals = {
                'name': f"VAT {rate}% ({'Sales' if use=='sale' else 'Purchase'})",
                'type_tax_use': use,
                'amount_type': 'percent',
                'amount': rate,
                'tax_group_id': group.id if group else False,
                'company_id': company.id,
                'active': True,
                'price_include': False,
            }
            tax = Tax.create(vals)
            # Set accounts on repartition lines
            account = acc_collected if use == 'sale' else acc_paid
            if account:
                (tax.invoice_repartition_line_ids | tax.refund_repartition_line_ids).filtered(
                    lambda l: l.repartition_type == 'tax'
                ).write({'account_id': account.id})

    # Final cleanup
    post_load_cleanup(cr, registry)
    _logger.info(" Fiji localization setup complete.")


def post_load_cleanup(cr, registry):
    """Final cleanup — ensures one active Sale + Purchase per rate and
    removes 'My Company' duplicates permanently."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    Tax = env['account.tax']
    Company = env['res.company']

    _logger.info(" Running final VAT cleanup...")

    try:
        my_company = Company.search([('name', '=', 'My Company')], limit=1)
        if my_company:
            my_taxes = Tax.search([('company_id', '=', my_company.id)])
            if my_taxes:
                _logger.info("🗑 Removing %s My Company taxes (post-CoA).", len(my_taxes))
                try:
                    my_taxes.write({'active': False})
                except Exception:
                    my_taxes.write({'active': False})
                env.cr.commit()

        # Keep only one Sale + Purchase per rate
        for rate in (0.0, 9.0, 12.5, 15.0):
            taxes = Tax.search([
                ('amount', '=', rate),
                ('country_id.code', '=', 'FJ'),
                ('type_tax_use', 'in', ['sale', 'purchase']),
                ('active', '=', True),
            ], order='id asc')

            if taxes:
                sale_keep = taxes.filtered(lambda t: t.type_tax_use == 'sale')[:1]
                purchase_keep = taxes.filtered(lambda t: t.type_tax_use == 'purchase')[:1]
                keep_ids = sale_keep.ids + purchase_keep.ids
                duplicates = taxes.filtered(lambda t: t.id not in keep_ids)
                if duplicates:
                    _logger.info("🗑 Archiving duplicate VAT %.1f%% taxes: %s", rate, duplicates.ids)
                    try:
                        duplicates.write({'active': False})
                    except Exception:
                        duplicates.write({'active': False})
                    env.cr.commit()

        _logger.info(" Final Fiji VAT cleanup complete — one Sale + one Purchase per rate remain.")
    except Exception as e:
        _logger.warning(" VAT cleanup skipped: %s", e)


# Override with a stricter, idempotent cleanup that merges duplicates safely.
def post_load_cleanup(cr, registry):  # noqa: F811 (intentional redefinition)
    """Merge duplicate Fiji VAT taxes and keep one canonical per rate/type.

    For each company and each (type_tax_use, amount):
    - Choose a canonical tax (prefer l10n_fj_minicoa XMLID, FRCS VAT group, active).
    - Reassign product customer/supplier taxes and fiscal position mappings
      from duplicates to the canonical one.
    - Update company default sale/purchase taxes if they point to duplicates.
    - Archive extras to avoid FK issues.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    Tax = env['account.tax']
    IMD = env['ir.model.data']
    Company = env['res.company']

    def _xmlid_module(tax):
        imd = IMD.search([('model', '=', 'account.tax'), ('res_id', '=', tax.id)], limit=1)
        return imd.module if imd else None

    def _score(t):
        s = 0
        if _xmlid_module(t) == 'l10n_fj_minicoa':
            s += 100
        if t.tax_group_id and t.tax_group_id.name in ('FRCS VAT', 'FRCS'):
            s += 10
        name = (t.name or '')
        if '(Fiji)' in name or 'FRCS' in name:
            s += 5
        if t.active:
            s += 1
        return s

    def _pick_canonical(taxes):
        return sorted(taxes, key=lambda x: (-_score(x), x.id))[0]

    _logger.info("Running post-load Fiji VAT duplicate merge...")

    try:
        # Remove base template noise on the placeholder 'My Company'
        base_co = Company.search([('name', '=', 'My Company')], limit=1)
        if base_co:
            leftovers = Tax.search([('company_id', '=', base_co.id)])
            if leftovers:
                leftovers.write({'active': False})

        for company in Company.search([]):
            # Ensure required taxes exist for this company before merging
            TaxGroup = env['account.tax.group']
            group = TaxGroup.search([('name', '=', 'FRCS VAT'), ('company_id', '=', company.id)], limit=1) \
                or env.ref('l10n_fj_minicoa.tax_group_vat', raise_if_not_found=False)
            def by_code(code):
                return env['account.account'].search([('code', '=', code), ('company_id', '=', company.id)], limit=1)
            acc_collected = by_code('21310')
            acc_paid = by_code('21330')
            for rate in (0.0, 9.0, 12.5, 15.0):
                for use in ('sale', 'purchase'):
                    exists = Tax.search([
                        ('company_id', '=', company.id),
                        ('type_tax_use', '=', use),
                        ('amount_type', '=', 'percent'),
                        ('amount', '=', rate),
                    ], limit=1)
                    if not exists:
                        vals = {
                            'name': f"VAT {rate}% ({'Sales' if use=='sale' else 'Purchase'})",
                            'type_tax_use': use,
                            'amount_type': 'percent',
                            'amount': rate,
                            'tax_group_id': group.id if group else False,
                            'company_id': company.id,
                            'active': True,
                            'price_include': False,
                        }
                        t = Tax.create(vals)
                        acc = acc_collected if use == 'sale' else acc_paid
                        if acc:
                            (t.invoice_repartition_line_ids | t.refund_repartition_line_ids).filtered(
                                lambda l: l.repartition_type == 'tax'
                            ).write({'account_id': acc.id})

            domain = [
                ('company_id', '=', company.id),
                ('type_tax_use', 'in', ['sale', 'purchase']),
                ('amount_type', '=', 'percent'),
            ]
            taxes = Tax.search(domain)
            buckets = {}
            for t in taxes:
                key = (t.type_tax_use, float(t.amount))
                buckets.setdefault(key, Tax.browse())
                buckets[key] |= t

            for (use, rate), recs in buckets.items():
                if len(recs) <= 1:
                    continue
                keep = _pick_canonical(recs)
                extras = recs - keep

                # Reassign product taxes (customer and supplier)
                PT = env['product.template'].with_context(active_test=False)
                for prod in PT.search([('company_id', '=', company.id), ('taxes_id', 'in', extras.ids)]):
                    prod.taxes_id = [(6, 0, ((prod.taxes_id - extras) | keep).ids)]
                for prod in PT.search([('company_id', '=', company.id), ('supplier_taxes_id', 'in', extras.ids)]):
                    prod.supplier_taxes_id = [(6, 0, ((prod.supplier_taxes_id - extras) | keep).ids)]

                # Reassign fiscal position mapping lines
                FPT = env['account.fiscal.position.tax']
                for line in FPT.search(['|', ('tax_src_id', 'in', extras.ids), ('tax_dest_id', 'in', extras.ids)]):
                    vals = {}
                    if line.tax_src_id in extras:
                        vals['tax_src_id'] = keep.id
                    if line.tax_dest_id in extras:
                        vals['tax_dest_id'] = keep.id
                    if vals:
                        line.write(vals)

                # Company defaults
                updates = {}
                if use == 'sale' and company.account_sale_tax_id in extras:
                    updates['account_sale_tax_id'] = keep.id
                if use == 'purchase' and company.account_purchase_tax_id in extras:
                    updates['account_purchase_tax_id'] = keep.id
                if updates:
                    company.write(updates)

                # Archive extras to avoid breaking history
                extras.write({'active': False})
                _logger.info("%s: keep %s for %s %.1f%%, archived %s", company.name, keep.id, use, rate, extras.ids)

        _logger.info("Fiji VAT duplicate merge complete.")
    except Exception as e:
        _logger.warning("VAT cleanup skipped: %s", e)


