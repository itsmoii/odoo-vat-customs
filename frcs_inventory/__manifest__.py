{
    "name": "FRCS Inventory",
    "version": "1.0.0",
    "summary": "Inventory extensions for FRCS compliance (GTIN, tax label, groundwork)",
    "author": "USP Team 10",
    "license": "LGPL-3",
    "depends": ["stock", "product"],  # base inventory & product models
    "data": [
        "views/product_views.xml",
        "report/product_master_report.xml",
        "views/menu_actions.xml",

    ],
    "installable": True,
    "application": False,
}
