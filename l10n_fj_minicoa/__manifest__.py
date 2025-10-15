{
    "name": "Fiji Mini Chart of Accounts (FRCS)",
    "summary": "Fiji fiscal localization: Mini CoA and FRCS VAT",
    "version": "1.0.4",
    "author": "Asifa + You",
    "category": "Accounting/Localizations/Account Charts",
    "countries": ["fj"],
    "license": "LGPL-3",
    "depends": [
        "account"
    ],
    "data": [
        "data/res_currency_data.xml",
        "data/tax_groups.xml",
        "data/patch_fj_tax_group.xml",
        # Load accounts BEFORE taxes so XML IDs like fj_21310/fj_21330 exist
        "data/template/account.account-fj_minicoa.csv",
        # Now load taxes that reference those accounts
        "data/taxes.xml",
        "views/account_tax_views.xml",
        "data/template/account_tax_template_data.xml",
        "data/account.account.tag.csv",
        "views/menu.xml"
    ],
    "demo": [],
    "installable": True,
    # Ensure our bootstrap runs after install
    "pre_init_hook": "pre_init_cleanup",
    "post_init_hook": "post_init_setup",
    # Keep auto_install simple; Odoo treats this as a boolean
    "auto_install": False,
    "application": False,
}
