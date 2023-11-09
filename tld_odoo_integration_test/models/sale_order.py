
from odoo import models, fields
import csv
from datetime import datetime, timedelta
import math


class SaleOrder(models.Model):
    _inherit = "sale.order"

    send_order_to_tld = fields.Boolean(
        string="TLD Order exported", default=False, copy=False, tracking=True)
    tld_order_processed = fields.Boolean(
        string="Order Processed", default=False)

    def export_sale_order_file_in_tld(self, sftp_server_id):
        sftp_server = self.env['sftp.syncing'].browse(sftp_server_id)
        file_name = '{0}{1}.csv'.format("so_", self.name)
        with open('/tmp/' + file_name, 'w') as file:
            writer = csv.writer(file)
            if self.partner_id and self.partner_id.parent_id:
                partner_shipping_name = self.partner_id.parent_id.name
            else:
                partner_shipping_name = self.partner_id.name if self.partner_id.name else self.partner_shipping_id.name or ""
            partner_shipping_street = self.partner_shipping_id.street or ""
            partner_shipping_street_2 = self.partner_shipping_id.street2 or ""
            company_name = ''
            partner_name = self.partner_id.name or ""
            partner_street = self.partner_id.street or ""
            partner_street_2 = self.partner_id.street2 or ""

            writer.writerow(
                ['Delivery Name', 'Delivery Address 1', 'Delivery Address 2', 'Delivery Suburb', 'Delivery State',
                 'Delivery Post Code',
                 'Quantity', 'Product Code', 'Sales Order Number', 'Delivery Email Address', 'Delivery Phone Number',
                 'Destination Country', 'Scheduled ship date', 'Item List Price', 'Company Name', 'Customer Name',
                 'Customer Address 1', 'Customer Address 2', 'Customer Suburb', 'Customer State', 'Customer Post Code',
                 'Default Invoice Currency', 'Delivery Instructions'])

            email = self.partner_shipping_id.email if self.partner_shipping_id.email else (
                self.partner_id.email or "")
            for line in self.order_line.filtered(lambda x: not x.is_delivery and x.product_id.type == 'product'):
                remain_quantity = line.product_uom_qty
                for i in range(math.ceil(remain_quantity / 999)):
                    if remain_quantity > 999:
                        product_qty = 999
                    else:
                        product_qty = remain_quantity
                    remain_quantity = remain_quantity - 999
                    writer.writerow([
                        partner_shipping_name, partner_shipping_street, partner_shipping_street_2,
                        self.partner_shipping_id.city or "", self.partner_shipping_id.state_id.code or ".",
                        self.partner_shipping_id.zip or "0", str(
                            product_qty) or "",
                        str(line.product_id.default_code), str(
                            self.name), email,
                        (self.partner_shipping_id.phone or self.partner_shipping_id.mobile or "").replace(
                            '+', ''),
                        self.partner_shipping_id.country_id.code or self.partner_id.country_id.code or "",
                        self.ship_order_date_3pl and datetime.strftime(
                            self.ship_order_date_3pl, '%d%m%Y') or "", line.price_unit,
                        company_name or "", partner_name, partner_street, partner_street_2, self.partner_id.city or "",
                        self.partner_id.state_id.code or ".", self.partner_id.zip or "0",
                        self.pricelist_id.currency_id.name, ""

                    ])
            file.close()
            sftp_client = sftp_server.connect_sftp()
            server_location = sftp_server.tld_export_sale_order_path + '/' + file_name
            sftp_server.export_file_to_sftp_server(
                sftp_client, '/tmp/' + file_name, server_location)
            self.send_order_to_tld = True
            if self._context.get('call_from_action', False):
                self.message_post(
                    body='Order exported to tld from action.:{0}'.format(file_name))
            else:
                self.message_post(
                    body='Order exported to tld after order confirm.:{0}'.format(file_name))

    def action_confirm(self):
        self.ship_order_date_3pl = datetime.now() + timedelta(days=30)
        val = super(SaleOrder, self).action_confirm()
        sftp_server_id = self.env['sftp.syncing'].search(
            [('store', '=', 'tld'), ('warehouse_id', '=', self.warehouse_id.id)], limit=1)
        if self.order_line.filtered(
                lambda x: not x.is_delivery and x.product_id.type == 'product') and not self.send_order_to_tld and sftp_server_id and not self.skip_send_order_to_3pl:
            self.export_sale_order_file_in_tld(sftp_server_id.id)
            self._cr.commit()
        return val
