# -*- coding: utf-8 -*-pack
# Part of Waoconnect. See LICENSE file for full copyright and licensing details.

{
    'name': 'TLD Odoo Integration',
    'version': '16.0.1.0.0',
    'category': 'Sales',
    'summary': """TLD Odoo Integration""",
    'description': """TLD Odoo Integration""",
    'author': "Waoconnect",
    'maintainer': 'Waoconnect',
    'website': 'https://www.waoconnect.com',
    'price': 215,
    'currency': 'AUD',
    'depends': ['delivery', 'sftp_server_connector', 'mrp', 'purchase',
                'common_fields_for_3pl_integration'],
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/sale_order.xml',
        'views/product_product.xml',
        'views/sftp_syncing.xml',
        'views/stock_picking.xml',
        'wizard/upload_products.xml',
        'wizard/export_sale_order_tld.xml',
        'views/purchase_order.xml',
    ],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': True,
    'images': [
        'static/description/Banner.jpg',
    ],

}
