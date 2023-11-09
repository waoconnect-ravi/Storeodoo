
from odoo import api, fields, models, _
import csv
from datetime import datetime
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger("TLD")


class SftpSyncing(models.Model):
    _inherit = "sftp.syncing"

    store = fields.Selection(
        selection_add=[("tld", "TLD")], ondelete={'tld': 'cascade'})
    tld_export_product_path = fields.Char(
        string="Export Product Directory Path")
    tld_export_sale_order_path = fields.Char(
        string="Export Sale Order Directory Path")
    tld_export_purchase_order_path = fields.Char(
        string="Export Purchase Order Directory Path")
    tld_import_despatch_details_of_order_path = fields.Char(
        string="Import Order's Despatch Details Directory Path")
    tld_import_product_inventory_adjustment_report_path = fields.Char(
        string="Import Product's Inventory Adjustment Report Path")
    tld_import_purchase_order_despatch_report_path = fields.Char(
        string="Import Purchase Order Despatch Report Path")

    def tld_create_schedule_actions(self):
        if not self.env['ir.cron'].search([('code', '=', "model.tld_despatch_report_fetch({})".format(self.id))]):
            cron_name = "TLD[{}] Fetch Despatch Report".format(self.name)
            code_method = "model.tld_despatch_report_fetch({})".format(self.id)
            self.create_cron_job(
                cron_name, code_method, interval_number=20, interval_type='minutes', numbercall=-1)

    @api.model
    def create(self, vals):
        tld = self.search([('store', '=', 'tld')])
        if vals.get('store') == 'tld' and tld:
            raise ValidationError(
                _("You can not create multiple SFTP records of TLD.\nSFTP with store = TLD is already created with name = {} and id = {}".format(
                    tld.name, tld.id)))
        return super(SftpSyncing, self).create(vals)

    def tld_despatch_report_fetch(self, sftp_id):
        sftp_server_id = self.browse(sftp_id)
        if sftp_server_id:
            sftp_client = sftp_server_id.connect_sftp()
            matched_files = sftp_server_id.get_all_files_and_folders_from_server_location(sftp_client,
                                                                                          sftp_server_id.tld_import_despatch_details_of_order_path,
                                                                                          match='.csv')
            server_dir = sftp_client.getcwd()
            if server_dir[-1] != '/':
                server_dir += '/'
            matched_files = matched_files[:2]
            for matched_file in matched_files:
                sftp_server_id.import_file_to_local_from_sftp(sftp_client, server_dir + matched_file,
                                                              '/tmp/' + matched_file)
            for matched_file in matched_files:
                try:
                    reader = csv.reader(open('/tmp/' + matched_file))
                    for data in reader:
                        if data[0] == 'Docket Docket No.':
                            continue
                        order = self.env['sale.order'].search(
                            [('name', '=', data[3].upper())], limit=1)
                        _logger.info(
                            "ORDER NO : {0} {1}".format(data[3], order))
                        if not order:
                            split_order_data = data[3].split("-")
                            if len(split_order_data) > 1:
                                order_name = split_order_data[0]
                                order = self.env['sale.order'].search(
                                    [('name', '=', order_name.upper())], limit=1)
                                _logger.info(
                                    "Sale ORDER NO : {}".format(order))
                        picking_ids = order.picking_ids.filtered(
                            lambda x: x.state not in ['done', 'cancel'])
                        _logger.info("Picking:{0}".format(picking_ids))
                        if order and picking_ids:
                            for line in order.order_line.filtered(lambda line: line.product_id.default_code == data[1]):
                                _logger.info("Line:{}".format(line))
                                total_done_qty = float(data[4])
                                if line.product_id.bom_ids:
                                    for move_line in line.move_ids.filtered(lambda mv: mv.state != 'done' and not mv.done_qty_3pl):
                                        single_bom_prd_qty = move_line.product_uom_qty / \
                                            (line.product_qty - line.qty_delivered)
                                        move_line.done_qty_3pl = total_done_qty * single_bom_prd_qty
                                else:
                                    for move_line in line.move_ids.filtered(lambda mv: mv.state != 'done' and not mv.done_qty_3pl):
                                        move_line.done_qty_3pl = total_done_qty
                                break
                            for picking in picking_ids:
                                picking.consignment_id = data[0]
                                picking.carrier_tracking_ref = data[6]
                                picking.carrier_3pl = data[5]
                                picking.date_of_shipped = datetime.strptime(str(data[2]),
                                                                            "%d/%m/%Y").date()  # data[2]#
                                if "tnt" in data[5].lower().replace(' ', ''):
                                    picking.tracking_url_tld_3pl = "https://www.tnt.com/express/en_in/site/shipping-tools/tracking.html?searchType=con&cons={}".format(
                                        data[6])
                                elif "toll" in data[5].lower().replace(' ', ''):
                                    picking.tracking_url_nzd_3pl = "https://www.mytoll.com/".format(
                                        data[6])
                                self.create_tld_shipping_method(
                                    picking, picking.carrier_3pl)
                                picking.name_3pl = 'tld'

                            order.tld_order_processed = True
                    sftp_server_id.rename_file_from_sftp_server(sftp_client, server_dir + matched_file,
                                                                server_dir + '/Archive/' + matched_file)
                    self._cr.commit()
                except Exception as e:
                    _logger.info(
                        "TLD Error While Fetch despatch CSV error = {}".format(e))
            self._cr.commit()
            sftp_client.close()

    def tld_validate_delivery_orders(self):
        pickings = self.env['stock.picking'].search(
            [('state', 'not in', ['done', 'cancel']), ('name_3pl', '=', 'tld'),
             ('move_ids.done_qty_3pl', '>', 0)], limit=150)
        for picking in pickings:
            rem = {}
            for move in picking.move_ids.search([('id', 'in', picking.move_ids.ids)],
                                                order="done_qty_3pl desc"):
                if move.done_qty_3pl >= move.product_uom_qty:
                    move.quantity_done = move.product_uom_qty
                    rem_qty = move.done_qty_3pl - move.quantity_done
                    move.done_qty_3pl = move.quantity_done
                    if rem_qty:
                        if rem.get(move.product_id.default_code):
                            rem[move.product_id.default_code] = rem[move.product_id.default_code] + rem_qty
                        else:
                            rem.update({move.product_id.default_code: rem_qty})
                elif move.done_qty_3pl < move.product_uom_qty:
                    move.done_qty_3pl = move.done_qty_3pl + \
                        rem.get(move.product_id.default_code, 0.0)
                    rem.pop(move.product_id.default_code, False)
                    if move.done_qty_3pl >= move.product_uom_qty:
                        move.quantity_done = move.product_uom_qty
                        rem_qty = move.done_qty_3pl - move.quantity_done
                        move.done_qty_3pl = move.quantity_done
                        if rem_qty:
                            if rem.get(move.product_id.default_code):
                                rem[move.product_id.default_code] = rem[move.product_id.default_code] + rem_qty
                            else:
                                rem.update(
                                    {move.product_id.default_code: rem_qty})
                    else:
                        move.quantity_done = move.done_qty_3pl
            rem_keys = [x for x in rem.keys()]
            for move in picking.move_ids.filtered(
                    lambda x: x.quantity_done != x.product_uom_qty and x.product_id.default_code in rem_keys):
                move.done_qty_3pl = move.done_qty_3pl + \
                    rem.get(move.product_id.default_code, 0.0)
                rem.pop(move.product_id.default_code, False)
                if move.done_qty_3pl >= move.product_uom_qty:
                    move.quantity_done = move.product_uom_qty
                    move.done_qty_3pl = move.quantity_done
                else:
                    move.quantity_done = move.done_qty_3pl

            picking._action_done()
            self._cr.commit()

    def create_tld_shipping_method(self, picking, carrier_3pl):
        delivery_carrier_obj = self.env['delivery.carrier']
        if carrier_3pl:
            delivery_carrier = delivery_carrier_obj.search(
                [('name', '=', carrier_3pl)], limit=1)
            sftp_server_id = self.env['sftp.syncing'].search(
                [('store', '=', 'tld')], limit=1)
            if delivery_carrier:
                picking.carrier_id = delivery_carrier.id
            else:

                delivery_carrier = delivery_carrier_obj.create({
                    'name': carrier_3pl,
                    'product_id': self.env.ref('tld_odoo_integration.tld_shipping_product').id,
                    'delivery_type': 'fixed',
                    'company_id': sftp_server_id.warehouse_id.company_id.id
                })
                picking.carrier_id = delivery_carrier.id

    def tld_purchase_order_despatch_report_fetch(self):
        sftp_server_id = self.env['sftp.syncing'].search(
            [('store', '=', 'tld')], limit=1)
        if sftp_server_id:
            sftp_client = sftp_server_id.connect_sftp()
            matched_files = sftp_server_id.get_all_files_and_folders_from_server_location(sftp_client,
                                                                                          sftp_server_id.tld_import_purchase_order_despatch_report_path,
                                                                                          match='.csv')
            server_dir = sftp_client.getcwd()
            if server_dir[-1] != '/':
                server_dir += '/'
            matched_files = matched_files[:2]
            for matched_file in matched_files:
                sftp_server_id.import_file_to_local_from_sftp(sftp_client, server_dir + matched_file,
                                                              '/tmp/' + matched_file)
            for matched_file in matched_files:
                try:
                    reader = csv.reader(open('/tmp/' + matched_file))
                    for data in reader:
                        if data[0] == 'Docket Docket No.':
                            continue
                        order = self.env['purchase.order'].search(
                            [('name', '=', data[3])], limit=1)
                        picking_ids = order.picking_ids.filtered(
                            lambda x: x.state not in ['done', 'cancel'])
                        if order and picking_ids:
                            for picking in picking_ids:
                                move_lines = picking.move_ids.filtered(
                                    lambda x: x.product_id.default_code == data[1] and not x.done_qty_3pl)
                                add_done_qty_3pl = False
                                if not move_lines:
                                    move_lines = picking.move_ids.filtered(
                                        lambda x: x.product_id.default_code == data[1] and x.done_qty_3pl)
                                    add_done_qty_3pl = True
                                if move_lines:
                                    picking.consignment_id = data[0]
                                    picking.carrier_tracking_ref = data[6]
                                    picking.carrier_3pl = data[5]
                                    picking.date_of_shipped = datetime.strptime(str(data[2]),
                                                                                "%d/%m/%Y").date()  # data[2]#
                                    if "tnt" in data[5].lower().replace(' ', ''):
                                        picking.tracking_url_tld_3pl = "https://www.tnt.com/express/en_in/site/shipping-tools/tracking.html?searchType=con&cons={}".format(
                                            data[6])
                                    elif "toll" in data[5].lower().replace(' ', ''):
                                        picking.tracking_url_nzd_3pl = "https://www.mytoll.com/".format(
                                            data[6])
                                    if add_done_qty_3pl:
                                        move_lines[0].done_qty_3pl += float(
                                            data[4])
                                    else:
                                        move_lines[0].done_qty_3pl = float(
                                            data[4])
                                    self.create_tld_shipping_method(
                                        picking, picking.carrier_3pl)
                                    picking.name_3pl = 'tld'

                    sftp_server_id.rename_file_from_sftp_server(sftp_client, server_dir + matched_file,
                                                                server_dir + '/Archive/' + matched_file)
                    self._cr.commit()
                except Exception as e:
                    _logger.info(
                        "TLD Error While Fetch despatch CSV error = {}".format(e))
            self._cr.commit()
            sftp_client.close()

    def tld_validate_purchase_orders(self):
        pickings = self.env['stock.picking'].search(
            [('state', 'not in', ['done', 'cancel']), ('name_3pl', '=', 'tld'),
             ('move_ids.done_qty_3pl', '>', 0)], limit=150)
        for picking in pickings:
            rem = {}
            for move in picking.move_ids.search([('id', 'in', picking.move_ids.ids)],
                                                order="done_qty_3pl desc"):
                if move.done_qty_3pl >= move.product_uom_qty:
                    move.quantity_done = move.product_uom_qty
                    rem_qty = move.done_qty_3pl - move.quantity_done
                    move.done_qty_3pl = move.quantity_done
                    if rem_qty:
                        if rem.get(move.product_id.default_code):
                            rem[move.product_id.default_code] = rem[move.product_id.default_code] + rem_qty
                        else:
                            rem.update({move.product_id.default_code: rem_qty})
                elif move.done_qty_3pl < move.product_uom_qty:
                    move.done_qty_3pl = move.done_qty_3pl + \
                        rem.get(move.product_id.default_code, 0.0)
                    rem.pop(move.product_id.default_code, False)
                    if move.done_qty_3pl >= move.product_uom_qty:
                        move.quantity_done = move.product_uom_qty
                        rem_qty = move.done_qty_3pl - move.quantity_done
                        move.done_qty_3pl = move.quantity_done
                        if rem_qty:
                            if rem.get(move.product_id.default_code):
                                rem[move.product_id.default_code] = rem[move.product_id.default_code] + rem_qty
                            else:
                                rem.update(
                                    {move.product_id.default_code: rem_qty})
                    else:
                        move.quantity_done = move.done_qty_3pl
            rem_keys = [x for x in rem.keys()]
            for move in picking.move_ids.filtered(
                    lambda x: x.quantity_done != x.product_uom_qty and x.product_id.default_code in rem_keys):
                move.done_qty_3pl = move.done_qty_3pl + \
                    rem.get(move.product_id.default_code, 0.0)
                rem.pop(move.product_id.default_code, False)
                if move.done_qty_3pl >= move.product_uom_qty:
                    move.quantity_done = move.product_uom_qty
                    move.done_qty_3pl = move.quantity_done
                else:
                    move.quantity_done = move.done_qty_3pl

            picking._action_done()
            self._cr.commit()
