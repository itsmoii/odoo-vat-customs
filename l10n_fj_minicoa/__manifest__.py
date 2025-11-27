{
    'name': 'Fiji Mini Chart of Accounts (FRCS)',
    'summary': 'Fiji fiscal localization: Mini CoA',
    'version': '18.0.1.0.0',
    'author': 'USP-FRCS IEP Team 2025',
    'license': 'LGPL-3',
    'category': 'Accounting/Localizations/Account Charts',
    'countries': ['fj'],
    'depends': [
        'account',
        'account_payment',
    ],
    'data': [
        'data/frcs_tax_group.xml',
        'data/taxes.xml',
        'data/template/account.account-fj_minicoa.csv',
        'data/res_currency_data.xml',
        'views/menu.xml',
        
    ],

    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_setup',
    'license': 'LGPL-3',
    'images': ['static/description/icon.png'],
}
