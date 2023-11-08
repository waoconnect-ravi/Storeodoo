
from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    product_status = fields.Selection(
        [('n', 'New'), ('m', 'Modify')], string="Product Status", default="n")

    def export_product_to_nzd(self, selected_products, sftp_server_id):
        products = self.env['product.product'].browse(
            selected_products).filtered(lambda x: x.type == 'product')
        sftp_object = self.env['sftp.syncing'].browse(sftp_server_id)
        file_name = 'products_' + fields.Datetime.now().strftime("%Y%m%d%H%M%S%f") + '.VCu'
        with open('/tmp/' + file_name, 'w') as file:
            for product in products:
                product_header_line = "{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15},{16},{17},{18},{19},{20},{21},{22},{23},{24},{25},{26},{27},{28},{29},{30},{31},{32},{33}".format(
                    product.default_code or '""', product.name, '""', product.weight or '""', '""',
                    product.standard_price or '""',
                    '""', '""', '""', '""', '""',
                    '""', '""', '""', '""', '""', '""', '""', '""', '""', '""', '""', '""', '""',
                    product.product_status or '""', '""',
                    '""', '""', '""', '""', '""', '""', '""', '""')
                file.write(product_header_line)
                file.write('\r\n')
                product.message_post(
                    body='Product exported to nzd successfully.:{0}'.format(file_name))
        file.close()
        sftp_client = sftp_object.connect_sftp()
        server_location = sftp_object.nzd_export_product_path + '/' + file_name
        sftp_object.export_file_to_sftp_server(
            sftp_client, '/tmp/' + file_name, server_location)
        return True
