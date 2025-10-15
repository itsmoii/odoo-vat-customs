from odoo import api, SUPERUSER_ID


def post_init_assign_taxes(cr, registry):
    """Assign both VAT 0% and VAT 12.5% to products that currently have no
    sales taxes configured (field ``taxes_id``).

    Uses XML IDs defined in this module's data/taxes.xml.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    tax0 = env.ref("finance_core.tax_vat_0", raise_if_not_found=False)
    tax125 = env.ref("finance_core.tax_vat_125", raise_if_not_found=False)

    if not (tax0 and tax125):
        return

    products = env["product.template"].search([("taxes_id", "=", False)])
    if products:
        products.write({"taxes_id": [(6, 0, [tax0.id, tax125.id])]})

