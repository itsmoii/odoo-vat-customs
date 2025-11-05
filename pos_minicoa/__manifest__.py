{
    "name": "POS Mini COA bootstrap",
    "summary": "Bootstraps accounting for POS: CoA, VAT 12.5/0, journals, payment methods, defaults",
    "version": "1.0.0",
    "author": "Asifa + You",
    "license": "LGPL-3",
    "depends": [
        "account",
        "point_of_sale",
        "l10n_fj_minicoa",
    ],
    "data": [
        "data/taxes.xml",
        "data/set_default_journal_accounts.xml",
        "views/accounting_menus.xml",
    ],
    "auto_install": True,
    "installable": True,
    "application": False,
    "post_init_hook": "post_init_setup",
}
