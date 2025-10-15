{
    'name': 'Custom POS',
    'version': '18.0.1.0.3',
    'summary': 'Base POS with customization for MSMEs',
    'description': 'Replaces default Odoo login page with role selection',
    'depends': ['point_of_sale', 'account'],
    'data': [
        'data/pos_categories.xml',
    ],
    'assets': {
        'point_of_sale.assets':[ 
            "custom_pos/static/src/js/frcs_payment.js",
            "custom_pos/static/src/lib/taxcore.min.js",
            "custom_pos/static/src/js/pos_category_filter.js",
            "custom_pos/static/src/js/product_price_override.js",
            "custom_pos/static/src/js/orderline_total_price.js",
          
            
        ],
        'point_of_sale.assets_qweb': [
             "custom_pos/static/src/xml/payment_screen_validate.xml",
             "custom_pos/static/src/xml/receipt_custom.xml",
             "custom_pos/static/src/xml/control_buttons_patch.xml",
             "custom_pos/static/src/xml/product_list_patch.xml",
             "custom_pos/static/src/xml/orderline_total_price.xml",
        ],


    },
    'installable': True,
    'application': True,
    'post_init_hook': 'post_init_hook',
}
