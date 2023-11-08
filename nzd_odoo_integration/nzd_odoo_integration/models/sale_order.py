
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    send_order_to_nzd = fields.Boolean(
        string="NZD Order exported", default=False, copy=False, tracking=True)
    nzd_order_processed = fields.Boolean(
        string="Order Processed", default=False)

    def export_sale_order_file_in_nzd(self, sftp_server_id):
        sftp_server = self.env['sftp.syncing'].browse(sftp_server_id)
        file_name = "{0}.{1}".format(self.name, "VCC")
        consignee_code = "{0}{1}".format(self.partner_shipping_id.display_name.replace(
            " ", "").replace(",", ""), self.partner_shipping_id.id)
        if self.partner_id and self.partner_id.parent_id:
            partner_shipping_name = self.partner_shipping_id.parent_id.name
        else:
            partner_shipping_name = self.partner_id.name if self.partner_id.name else self.partner_shipping_id.name or ""
        partner_shipping_street = '""'
        partner_shipping_street2 = '""'
        if self.partner_shipping_id.street:
            partner_shipping_street = self.partner_shipping_id.street.replace(
                ",", "")
        if self.partner_shipping_id.street2:
            partner_shipping_street2 = self.partner_shipping_id.street2.replace(
                ",", "")
        order_header_line = "{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15},{16},{17},{18},{19},{20},{21},{22},{23},{24},{25},{26},{27},{28},{29},{30},{31},{32},{33},{34},{35},{36},{37},{38},{39},{40},{41},{42},{43},{44},{45},{46},{47},{48},{49},{50}".format(
            'SOH', self.name, '""', '""', '""',
            consignee_code,
            partner_shipping_name or '""',
            partner_shipping_street,
            partner_shipping_street2, '""', '""', '""', '""', '""', '""', '""', "1", '""', '""',
            self.date_order.strftime(
                "%d/%m/%Y"), self.date_order.strftime("%d/%m/%Y"), '""', '""', '""', '""', 0, '""',
            '""', '""', '""', '""', '""', '""', '""',
            '""', "Parcel Express", '""', '""', '""', self.partner_shipping_id.city or '""', '""', '""', '""',
            '""', '""', '""', '""', '""', '""', '""', '""')

        with open('/tmp/' + file_name, 'w') as file:
            file.write(order_header_line)
            file.write('\r\n')
            line_count = 0
            for line in self.order_line.filtered(lambda x: not x.is_delivery and x.product_id.type == 'product'):
                if line.product_id.bom_ids:
                    for move_id in line.move_ids:
                        line_count += 1
                        line_price = (line.product_uom_qty * line.price_unit) / sum(
                            line.move_ids.mapped('product_uom_qty'))
                        order_product_line = "{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15},{16},{17},{18},{19},{20},{21},{22},{23},{24},{25},{26},{27},{28},{29},{30},{31},{32},{33},{34},{35}".format(
                            'SOL', self.name, line_count, '""', '""', move_id.product_id.default_code or '""',
                            move_id.product_id.name or '""', '""',
                            int(move_id.product_uom_qty) or '""',
                            '""', line_price or '""', 0, line_price or '""', line_price or '""', '""', '""',
                            '""', '""', '""', 0, 0, '""', '""', '""', '""', '""', '""', '""', '""', '""', '""', '""',
                            '""',
                            '""', '""', '""')
                        file.write(order_product_line)
                        file.write('\r\n')
                else:
                    line_count += 1
                    order_product_line = "{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15},{16},{17},{18},{19},{20},{21},{22},{23},{24},{25},{26},{27},{28},{29},{30},{31},{32},{33},{34},{35}".format(
                        'SOL', self.name, line_count, '""', '""', line.product_id.default_code or '""',
                        line.product_id.name or '""', '""',
                        int(line.product_uom_qty) or '""',
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

    def action_confirm(self):
        val = super(SaleOrder, self).action_confirm()
        sftp_server_id = self.env['sftp.syncing'].search(
            [('store', '=', 'nzd'), ('warehouse_id', '=', self.warehouse_id.id)])
        if self.order_line.filtered(
                lambda x: not x.is_delivery and x.product_id.type == 'product') and not self.send_order_to_nzd and sftp_server_id and not self.skip_send_order_to_3pl:
            self.export_sale_order_file_in_nzd(sftp_server_id.id)
            self._cr.commit()
        return val
