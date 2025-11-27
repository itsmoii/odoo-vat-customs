{
    "name": "FRCS POS Mini COA bootstrap",
    "summary": "Bootstraps accounting for POS: CoA, VAT 12.5/0, journals, payment methods, defaults",
    "version": "18.0.1.0.0",
    "author": "USP-FRCS IEP Team 2025",
    "license": "LGPL-3",
    'category': 'Accounting/Localizations',
    "depends": [
        "account",
        "point_of_sale",
        "l10n_fj_minicoa",
    ],
    "data": [
        "data/set_default_journal_accounts.xml",
        "views/accounting_menus.xml",
    ],
    'demo': [],
    "auto_install": True,
    "application": False,
    "post_init_hook": "post_init_setup",
    'license': 'LGPL-3',
    'images': ['static/description/icon.png'],
}
