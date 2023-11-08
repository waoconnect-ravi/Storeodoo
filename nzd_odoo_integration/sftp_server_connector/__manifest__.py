# -*- coding: utf-8 -*-pack
# Part of Waoconnect. See LICENSE file for full copyright and licensing details.

{
    'name': 'SFTP Server Connect',
    'version': '16.0.1.0.0',
    'category': "",
    'summary': """SFTP Server Connect""",
    'description': """SFTP Server Connect""",
    'author': "Waoconnect",
    'maintainer': 'Waoconnect',
    'website': 'https://www.waoconnect.com',
    'depends': ['base', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/sftp_syncing.xml',
    ],
    "external_dependencies": {
        "python": ["paramiko"],
    },
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': True,
}
