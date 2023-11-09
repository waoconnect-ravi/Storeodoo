
from odoo import fields, models
import csv


class ProductProduct(models.Model):
    _inherit = 'product.product'

    tld_product_length = fields.Char(string="Length")
    tld_product_height = fields.Char(string="Height")
    tld_product_width = fields.Char(string="Width")

    def export_product_file_in_tld(self, selected_products, sftp_server_id):
        products = self.env['product.product'].browse(selected_products).filtered(lambda x: x.type == 'product')
        sftp_server = self.env['sftp.syncing'].browse(sftp_server_id)

        file_name = 'products_' + fields.Datetime.now().strftime("%Y%m%d%H%M%S%f") + '.csv'
        with open('/tmp/' + file_name, 'w') as file:
            writer = csv.writer(file)
            writer.writerow(
                ['Product Code', 'Item Description', 'Quantity UM', 'Length', 'Width',
                 'Height',
                 'Dimension UM', 'Weight of Item', 'Weight UM', 'Item List Price', 'Harmonize Code',
                 'items per carton', 'cartons per layer', 'weight of carton', 'layers per pallet',
                 'weight of pallet',
                 ])
            for product in products:
                writer.writerow([
                    product.default_code or '', product.name or '', "", product.tld_product_length or '', product.tld_product_width or '', product.tld_product_height or '', "", product.weight or '', "", product.lst_price or '',
                    product.hs_code or '',
                    "", "", "", "", ""
                ])
                product.message_post(body='Product exported to tld successfully.:{0}'.format(file_name))
        sftp_client = sftp_server.connect_sftp()
        server_location = sftp_server.tld_export_product_path + '/' + file_name
        sftp_server.export_file_to_sftp_server(sftp_client, '/tmp/' + file_name, server_location)
        self._cr.commit()
