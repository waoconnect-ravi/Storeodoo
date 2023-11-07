# -*- coding: utf-8 -*-pack
# Part of Waoconnect. See LICENSE file for full copyright and licensing details.

{
    'name': 'NZD Odoo Integration',
    'version': '16.0.1.0.0',
    'category': "Sales",
    'summary': """NZD Odoo Integration""",
    'description': """NZD Odoo Integration""",
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
        'view/sale_order.xml',
        'view/purchase_order.xml',
        'view/sftp_syncing.xml',
        'view/product_product.xml',
        'wizard/upload_products_to_nzd.xml',
        'wizard/export_sale_order_nzd.xml',
        'view/stock_picking.xml'
    ],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': True,
    'images': [
        'static/description/Banner.jpg',
    ],
}
