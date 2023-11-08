
from odoo import api, fields, models
import csv
import math
from datetime import datetime


class StockPicking(models.Model):
    _inherit = "stock.picking"

    consignment_id = fields.Char(string="Consignment ID")
    carrier_3pl = fields.Char(string="Carrier 3pl")
    date_of_shipped = fields.Date(string="Shipped Date")
    tracking_url_tld_3pl = fields.Char(
        string="Tracking URL TLD 3pl", copy=False)
    name_3pl = fields.Char(string="Name 3PL", copy=False)
    tld_3pl = fields.Boolean(string="TLD 3PL", default=False,
                             compute="_compute_set_boolean_based_on_tld_warehouse")

    send_order_to_tld = fields.Boolean(
        string="TLD Order exported", default=False, copy=False, tracking=True)
    tld_order_processed = fields.Boolean(
        string="Order Processed", default=False)

    def export_sale_order_file_in_tld(self, sftp_server_id=False):
        sftp_server = self.env['sftp.syncing'].search(
            [('store', '=', 'tld')], limit=1)
        file_name = '{0}{1}.csv'.format("so_", self.origin)
        with open('/tmp/' + file_name, 'w') as file:
            writer = csv.writer(file)
            if self.partner_id and self.partner_id.parent_id:
                partner_shipping_name = self.partner_id.parent_id.name
            else:
                partner_shipping_name = self.partner_id.name
            partner_shipping_street = self.partner_id.street or ""
            partner_shipping_street_2 = self.partner_id.street2 or ""
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

            email = self.partner_id.email if self.partner_id.email else (
                self.partner_id.email or "")
            for line in self.move_ids.filtered(lambda x: x.sale_line_id.product_id.bom_ids).mapped('sale_line_id'):
                remain_quantity = line.product_uom_qty - line.qty_delivered
                for i in range(math.ceil(remain_quantity / 999)):
                    if remain_quantity > 999:
                        product_qty = 999
                    else:
                        product_qty = remain_quantity
                    remain_quantity = remain_quantity - 999
                    writer.writerow([
                        partner_shipping_name, partner_shipping_street, partner_shipping_street_2,
                        self.partner_id.city or "", self.partner_id.state_id.code or ".",
                        self.partner_id.zip or "0", str(product_qty) or "",
                        str(line.product_id.default_code), str(
                            "{0}-{1}".format(self.origin, self.id)), email,
                        (self.partner_id.phone or self.partner_id.mobile or "").replace(
                            '+', ''),
                        self.partner_id.country_id.code or self.partner_id.country_id.code or "",
                        self.scheduled_date and datetime.strftime(
                            self.scheduled_date, '%d%m%Y') or "", line.price_unit,
                        company_name or "", partner_name, partner_street, partner_street_2, self.partner_id.city or "",
                        self.partner_id.state_id.code or ".", self.partner_id.zip or "0",
                        self.sale_id.pricelist_id.currency_id.name, ""

                    ])
            for line in self.move_ids.filtered(lambda x: not x.sale_line_id.product_id.bom_ids):
                remain_quantity = line.product_uom_qty
                for i in range(math.ceil(remain_quantity / 999)):
                    if remain_quantity > 999:
                        product_qty = 999
                    else:
                        product_qty = remain_quantity
                    remain_quantity = remain_quantity - 999
                    writer.writerow([
                        partner_shipping_name, partner_shipping_street, partner_shipping_street_2,
                        self.partner_id.city or "", self.partner_id.state_id.code or ".",
                        self.partner_id.zip or "0", str(product_qty) or "",
                        str(line.product_id.default_code), str(
                            "{0}-{1}".format(self.origin, self.id)), email,
                        (self.partner_id.phone or self.partner_id.mobile or "").replace(
                            '+', ''),
                        self.partner_id.country_id.code or self.partner_id.country_id.code or "",
                        self.scheduled_date and datetime.strftime(
                            self.scheduled_date, '%d%m%Y') or "",
                        line.sale_line_id.price_unit,
                        company_name or "", partner_name, partner_street, partner_street_2, self.partner_id.city or "",
                        self.partner_id.state_id.code or ".", self.partner_id.zip or "0",
                        self.sale_id.pricelist_id.currency_id.name, ""

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

    @api.depends('picking_type_id')
    def _compute_set_boolean_based_on_tld_warehouse(self):
        for rec in self:
            sftp_server_id = self.env['sftp.syncing'].search(
                [('store', '=', 'tld')], limit=1)
            if rec.picking_type_id.warehouse_id == sftp_server_id.warehouse_id:
                rec.tld_3pl = True
            else:
                rec.tld_3pl = False
