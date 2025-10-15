{
"name": "Mini Supermarket Finance",
"version": "18.0.3.0.0",
"summary": "Simple finance for mini supermarkets: auto log POS sales and purchases",
"author": "Odoo Finance Module Developer",
"license": "LGPL-3",
"category": "Accounting",
"depends": ["base", "point_of_sale", "stock", "purchase", "purchase_stock", "account", "sale"],
"data": [
 "security/ir.model.access.csv",
 "security/finance_security.xml",
 "data/finance_sequence.xml",
 "data/taxes.xml",
 # Temporarily disabled to bypass model resolution timing issues during upgrade
 # "views/finance_menus.xml",
 "views/finance_views.xml",
 "views/finance_reports.xml",
 "views/finance_dashboard.xml",
 "views/finance_sales_details.xml",
 "views/finance_sales_page.xml",
 "views/finance_ap_details.xml",
 "views/account_journal_default_accounts.xml",

],
"assets": {
    "web.assets_backend": [
        "finance_core/static/src/scss/finance_dashboard.scss",
    ]
},
"installable": True,
"application": True,
"post_init_hook": "post_init_assign_taxes",
}
