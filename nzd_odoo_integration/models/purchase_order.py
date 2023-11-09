
from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    nzd_purchase_order_processed = fields.Boolean(
        string="Purchase Order Processed", default=False)

    def export_purchase_order_file_in_nzd(self):
        sftp_object = self.env['sftp.syncing'].sudo().search(
            [('store', '=', 'nzd')], limit=1)
        file_name = "{0}.{1}".format(self.name, "VCa")
        purchase_order_header_line = "{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13}".format('GIAH',
                                                                                                          self.name,
                                                                                                          self.date_order.strftime(
                                                                                                              "%d/%m/%Y"),
                                                                                                          self.date_planned.strftime(
                                                                                                              "%d/%m/%Y"),
                                                                                                          '""',
                                                                                                          self.partner_id.name,
                                                                                                          '""', '""',
                                                                                                          '""', '""',
                                                                                                          '""', '""',
                                                                                                          '""', '""')

        with open('/tmp/' + file_name, 'w') as file:
            file.write(purchase_order_header_line)
            file.write('\r\n')
            line_count = 0
            for line in self.order_line:
                line_count += 1
                purchase_order_product_line = "{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15},{16},{17},{18},{19},{20},{21},{22},{23},{24},{25}".format(
                    'GIAL', self.name, line_count, line.product_id.default_code or '""', line.product_id.name,
                    line.product_uom_qty, line.product_id.weight or '""', '""', '""', '""', '""', '""', '""', '""', '""', '""',
                    '""', '""', '""', '""', '""', '""', '""', '""', '""', '""',
                )
                file.write(purchase_order_product_line)
                file.write('\r\n')
            file.close()
            sftp_client = sftp_object.connect_sftp()
            server_location = sftp_object.nzd_export_purchase_order_path + '/' + file_name
            sftp_object.export_file_to_sftp_server(
                sftp_client, '/tmp/' + file_name, server_location)
            self.message_post(
                body='Purchase Order exported to NZD Successfully.')
