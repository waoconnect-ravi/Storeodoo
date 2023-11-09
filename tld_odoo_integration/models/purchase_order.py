
from odoo import models
import csv


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def export_purchase_order_file_in_tld(self):
        sftp_server_id = self.env['sftp.syncing'].search(
            [('store', '=', 'tld')], limit=1)
        file_name = '{0}{1}.csv'.format("po_", self.name)
        with open('/tmp/' + file_name, 'w') as file:
            writer = csv.writer(file)

            writer.writerow(
                ['Line ID', 'Company Name', 'Street Address', 'City', 'Zip', 'Product Code', 'Quantity', 'Order ID', 'PO Date', ])
            line_id = 0
            for product in self.order_line:
                line_id += 1
                writer.writerow([
                    line_id, self.company_id.name, self.company_id.street or "", self.company_id.city or "", self.company_id.zip or "", product.product_id.default_code or "", product.product_qty or "", self.name or "",
                    self.date_order or ""])

            file.close()
            self.message_post(body='Order exported to TLD Successfully.')
            sftp_client = sftp_server_id.connect_sftp()
            server_location = sftp_server_id.tld_export_purchase_order_path + '/' + file_name
            sftp_server_id.export_file_to_sftp_server(
                sftp_client, '/tmp/' + file_name, server_location)
            return True
