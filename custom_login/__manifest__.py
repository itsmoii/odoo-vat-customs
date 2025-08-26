{
    'name': 'Custom Login',
    'version': '1.0',
    'category': 'Website',
    'summary': 'Custom login page with role selection',
    'description': 'Replaces default Odoo login page with role selection',
    'depends': ['base', 'web'],
    'data': [
        'views/login_template.xml',
    ],
    'installable': True,
    'application': False,
}
