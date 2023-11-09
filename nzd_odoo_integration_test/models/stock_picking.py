
from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    name_3pl = fields.Char(string="Name 3PL", copy=False)
    nzd_delivery_validate = fields.Boolean(
        string="NZD Delivery Validated", default=False)
    date_of_shipped = fields.Date(string="Shipped Date")
    nzd_carrier = fields.Char("NZD Carrier", copy=False)
    tracking_url_nzd_3pl = fields.Char(
        string="Tracking Url NZD 3pl", copy=False)
    nzd_3pl = fields.Boolean(string="NZD 3PL", default=False,
                             compute="_compute_set_boolean_based_on_nzd_warehouse")

    send_order_to_nzd = fields.Boolean(
        string="NZD Order exported", default=False, copy=False, tracking=True)
    nzd_order_processed = fields.Boolean(
        string="Order Processed", default=False, copy=False)

    def export_sale_order_file_in_nzd(self, sftp_server_id=False):
        sftp_server_id = self.env['sftp.syncing'].search(
            [('store', '=', 'nzd')], limit=1)
        sftp_server = self.env['sftp.syncing'].browse(sftp_server_id)
        file_name = "{0}.{1}".format(self.origin, "VCC")
        consignee_code = "{0}{1}".format(self.partner_id.display_name.replace(" ", "").replace(",", ""),
                                         self.partner_id.id)
        if self.partner_id and self.partner_id.parent_id:
            partner_shipping_name = self.partner_id.parent_id.name
        else:
            partner_shipping_name = self.partner_id.name if self.partner_id.name else self.partner_id.name or ""
        partner_shipping_street = '""'
        partner_shipping_street2 = '""'
        if self.partner_id.street:
            partner_shipping_street = self.partner_id.street.replace(",", "")
        if self.partner_id.street2:
            partner_shipping_street2 = self.partner_id.street2.replace(",", "")
        order_header_line = "{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15},{16},{17},{18},{19},{20},{21},{22},{23},{24},{25},{26},{27},{28},{29},{30},{31},{32},{33},{34},{35},{36},{37},{38},{39},{40},{41},{42},{43},{44},{45},{46},{47},{48},{49},{50}".format(
            'SOH', "{0}-{1}".format(self.origin, self.id), '""', '""', '""',
            consignee_code,
            partner_shipping_name or '""',
            partner_shipping_street,
            partner_shipping_street2, '""', '""', '""', '""', '""', '""', '""', "1", '""', '""',
            self.scheduled_date.strftime(
                "%d/%m/%Y"), self.scheduled_date.strftime("%d/%m/%Y"), '""', '""', '""', '""', 0, '""',
            '""', '""', '""', '""', '""', '""', '""',
            '""', "Parcel Express", '""', '""', '""', self.partner_id.city or '""', '""', '""', '""',
            '""', '""', '""', '""', '""', '""', '""', '""')

        with open('/tmp/' + file_name, 'w') as file:
            file.write(order_header_line)
            file.write('\r\n')
            line_count = 0
            for line in self.move_ids.filtered(lambda x: x.sale_line_id.product_id.bom_ids).mapped('sale_line_id'):
                for move_id in line.move_ids:
                    line_count += 1
                    remaining_quantity = line.product_uom_qty - line.qty_delivered
                    line_price = (remaining_quantity * line.price_unit) / sum(
                        line.move_ids.mapped('product_uom_qty'))
                    order_product_line = "{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15},{16},{17},{18},{19},{20},{21},{22},{23},{24},{25},{26},{27},{28},{29},{30},{31},{32},{33},{34},{35}".format(
                        'SOL', "{0}-{1}".format(
                            self.origin, self.id), line_count, '""', '""', move_id.product_id.default_code or '""',
                        move_id.product_id.name or '""', '""',
                        int(move_id.product_uom_qty) or '""',
                        '""', line_price or '""', 0, line_price or '""', line_price or '""', '""', '""',
                        '""', '""', '""', 0, 0, '""', '""', '""', '""', '""', '""', '""', '""', '""', '""', '""',
                        '""',
                        '""', '""', '""')
                    file.write(order_product_line)
                    file.write('\r\n')
            for line in self.move_ids.filtered(lambda x: not x.sale_line_id.product_id.bom_ids):
                line_count += 1
                qty = sum(line.mapped('product_uom_qty'))
                order_product_line = "{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15},{16},{17},{18},{19},{20},{21},{22},{23},{24},{25},{26},{27},{28},{29},{30},{31},{32},{33},{34},{35}".format(
                    'SOL', "{0}-{1}".format(
                        self.origin, self.id), line_count, '""', '""', line.product_id.default_code or '""',
                    line.product_id.name or '""', '""',
                    int(qty) or '""',
                    '""', line.price_unit or '""', 0, line.price_unit or '""', line.price_unit or '""', '""', '""',
                    '""', '""', '""', 0, 0, '""', '""', '""', '""', '""', '""', '""', '""', '""', '""', '""', '""',
                    '""', '""', '""')
                file.write(order_product_line)
                file.write('\r\n')
            file.close()
            sftp_client = sftp_server.connect_sftp()
            server_location = sftp_server.nzd_export_sale_order_path + '/' + file_name
            sftp_server.export_file_to_sftp_server(
                sftp_client, '/tmp/' + file_name, server_location)
            self.send_order_to_nzd = True
            if self._context.get('call_from_action', False):
                self.message_post(
                    body='Order exported to nzd from action.:{0}'.format(file_name))
            else:
                self.message_post(
                    body='Order exported to nzd after order confirm.:{0}'.format(file_name))

    @api.depends('picking_type_id')
    def _compute_set_boolean_based_on_nzd_warehouse(self):
        for rec in self:
            sftp_server_id = self.env['sftp.syncing'].search(
                [('store', '=', 'nzd')], limit=1)
            if rec.picking_type_id.warehouse_id == sftp_server_id.warehouse_id:
                rec.nzd_3pl = True
            else:
                rec.nzd_3pl = False
