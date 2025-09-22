{
    'name': 'Custom POS',
    'version': '18.0.1.0.2',
    'summary': 'Base POS with customization for MSMEs',
    'description': 'Replaces default Odoo login page with role selection',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale.assets':[
            "custom_pos/static/src/js/frcs_payment.js",
            "custom_pos/static/src/lib/taxcore.min.js",
          
            
        ],
        'point_of_sale.assets_qweb': [
             "custom_pos/static/src/xml/payment_screen_validate.xml",
        ],


    },
    'installable': True,
    'application': True,
}
