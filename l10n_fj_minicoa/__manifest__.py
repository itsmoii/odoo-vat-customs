{
    'name': 'Fiji Mini Chart of Accounts (FRCS)',
    'summary': 'Fiji fiscal localization: Mini CoA and FRCS VAT configuration',
    'version': '1.0.6',
    'author': 'Asifa Hanif',
    'license': 'LGPL-3',
    'category': 'Accounting/Localizations/Account Charts',
    'countries': ['fj'],
    'depends': [
        'account',
    ],
    'data': [
        # --- Core data files ---
        'data/res_currency_data.xml',
        # --- Chart of Accounts Templates ---
        'data/template/account.account-fj_minicoa.csv',
        'views/menu.xml',
    ],

    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,

    # Hooks removed: tax data now lives in frcs_inventory
}
