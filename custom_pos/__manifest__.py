{
    'name': 'Custom POS',
    'version': '18.0.1.0.2',
    'summary': 'Base POS with customization for MSMEs',
    'description': 'Replaces default Odoo login page with role selection',
    'depends': ['point_of_sale'],
    'data': [
        "security/ir.model.access.csv"
    ],
    'assets': {
        'point_of_sale.assets_prod': [
            "custom_pos/static/src/css/pos_ui.css",
            "custom_pos/static/src/js/frcs_payment.js",
            "custom_pos/static/src/js/frcs_ticketscreen.js",
            "custom_pos/static/src/xml/frcs_taxcore.xml",
            "custom_pos/static/src/xml/frcs_ticketscreen.xml",
            "custom_pos/static/src/xml/frcs_receiptscreen.xml",
            "custom_pos/static/src/xml/frcs_actionpad.xml",
            
        ],
        'point_of_sale.assets': [
            "custom_pos/static/src/js/frcs_payment.js",
            "custom_pos/static/src/js/frcs_ticketscreen.js",
            "custom_pos/static/src/xml/frcs_taxcore.xml",
            "custom_pos/static/src/xml/frcs_ticketscreen.xml",
            "custom_pos/static/src/xml/frcs_receiptscreen.xml",
            "custom_pos/static/src/xml/frcs_actionpad.xml",
        ],
        'point_of_sale.assets_qweb': [
            "custom_pos/static/src/xml/frcs_taxcore.xml",
            "custom_pos/static/src/xml/frcs_ticketscreen.xml",
            "custom_pos/static/src/xml/frcs_receiptscreen.xml",
            "custom_pos/static/src/xml/frcs_actionpad.xml",
        ],

    },
    'installable': True,
    'application': True,
}
