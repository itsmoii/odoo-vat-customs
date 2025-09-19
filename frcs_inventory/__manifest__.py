{
    "name": "FRCS Inventory",
    "version": "1.0.0",
    "summary": "Inventory extensions for FRCS compliance (GTIN, tax label, groundwork)",
    "author": "USP Team 10",
    "license": "LGPL-3",
    "depends": ["stock", "product", "account"],  # needs account.tax
    "data": [
        "data/taxes.xml",
        "views/product_views.xml",
        "report/product_master_report.xml",
        "views/menu_actions.xml",

    ],
    "installable": True,
    "application": False,
    "post_init_hook": "post_init_hook",
}
