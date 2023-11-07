
from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger("NZD")


class SftpSyncing(models.Model):
    _inherit = "sftp.syncing"

    store = fields.Selection(
        selection_add=[("nzd", "NZD")], ondelete={'nzd': 'cascade'})
    nzd_export_product_path = fields.Char(
        string="Export Product Directory Path")
    nzd_export_sale_order_path = fields.Char(
        string="Export Sale Order Directory Path")
    nzd_export_purchase_order_path = fields.Char(
        string="Export Purchase Order Directory Path")
    nzd_import_despatch_details_of_order_path = fields.Char(
        string="Import Order's Despath Details Directory Path")
    nzd_import_product_inventory_adjustment_report_path = fields.Char(
        string="Import Product's Inventory Adjustment Report Path")

    def nzd_create_schedule_actions(self):
        if not self.env['ir.cron'].search([('code', '=', "model.nzd_despatch_report_fetch({})".format(self.id))]):
            cron_name = "nzd[{}] Fetch Despatch Report".format(self.name)
            code_method = "model.nzd_despatch_report_fetch({})".format(self.id)
            self.create_cron_job(
                cron_name, code_method, interval_number=20, interval_type='minutes', numbercall=-1)

    @api.model
    def create(self, vals):
        nzd = self.search([('store', '=', 'nzd')])
        if vals.get('store') == 'nzd' and nzd:
            raise ValidationError(
                _("You can not create multiple SFTP records of NZD.\nSFTP with store = NZD is already created with name = {} and id = {}".format(
                    nzd.name, nzd.id)))
        return super(SftpSyncing, self).create(vals)

    def nzd_despatch_report_fetch(self, sftp_id):
        sftp_server_id = self.browse(sftp_id)
        if sftp_server_id:
            sftp_client = sftp_server_id.connect_sftp()
            matched_files = sftp_server_id.get_all_files_and_folders_from_server_location(sftp_client,
                                                                                          sftp_server_id.nzd_import_despatch_details_of_order_path,
                                                                                          match='.VCh')
            server_dir = sftp_client.getcwd()
            if server_dir[-1] != '/':
                server_dir += '/'
            matched_files = matched_files[:2]
            for matched_file in matched_files:
                sftp_server_id.import_file_to_local_from_sftp(sftp_client, server_dir + matched_file,
                                                              '/tmp/' + matched_file)
            for matched_file in matched_files:
                try:
                    reader = (open('/tmp/' + matched_file))
                    order = False
                    picking_ids = False
                    for data in reader:
                        if len(data) > 8:
                            data = data.split(',')
                            if data[0] == 'SOH':
                                order = self.env['sale.order'].search(
                                    [('name', '=', data[1].upper())], limit=1)
                                if not order:
                                    split_order_data = data[1].split("-")
                                    if len(split_order_data) > 1:
                                        order_name = split_order_data[0]
                                        order = self.env['sale.order'].search([('name', '=', order_name.upper())],
                                                                              limit=1)
                                picking_ids = order.picking_ids.filtered(
                                    lambda x: x.state not in ['done', 'cancel'])
                                if picking_ids:
                                    nzd_tracking_ref = data[36]
                                    date_of_shipped = datetime.strptime(
                                        str(data[21]), "%d/%m/%y").date()
                                    nzd_carrier_3pl = data[35]
                            if order and picking_ids and data[0] == 'SOL':
                                for picking in picking_ids:
                                    move_lines = picking.move_ids.filtered(
                                        lambda x: x.product_id.default_code == data[5] and not x.done_qty_3pl)
                                    add_done_qty_3pl = False
                                    if not move_lines:
                                        move_lines = picking.move_ids.filtered(
                                            lambda x: x.product_id.default_code == data[5] and x.done_qty_3pl)
                                        add_done_qty_3pl = True
                                    if move_lines:
                                        picking.carrier_tracking_ref = nzd_tracking_ref
                                        picking.nzd_carrier = nzd_carrier_3pl
                                        if "titus" in nzd_carrier_3pl.lower().replace(' ', ''):
                                            picking.tracking_url_nzd_3pl = " "
                                        elif "parcel" in nzd_carrier_3pl.lower().replace(' ', ''):
                                            picking.tracking_url_nzd_3pl = "https://www.pelcs.co.nz/TrackEnq.aspx?ref={}".format(
                                                picking.carrier_tracking_ref)
                                        elif "mainfreight" in nzd_carrier_3pl.lower().replace(' ', ''):
                                            picking.tracking_url_nzd_3pl = "https://www.mainfreight.com/track"
                                        elif "dailyfreight" in nzd_carrier_3pl.lower().replace(' ', ''):
                                            picking.tracking_url_nzd_3pl = "https://www.mainfreight.com/track"
                                        picking.date_of_shipped = date_of_shipped
                                        if add_done_qty_3pl:
                                            move_lines[0].done_qty_3pl += float(
                                                data[9])
                                        else:
                                            move_lines[0].done_qty_3pl = float(
                                                data[9])
                                        self.create_nzd_shipping_method(
                                            picking, picking.nzd_carrier)
                                        picking.name_3pl = 'NZD'
                                        picking.nzd_delivery_validate = False

                                order.nzd_order_processed = True
                    sftp_server_id.rename_file_from_sftp_server(sftp_client, server_dir + matched_file,
                                                                server_dir + '/Archive/' + matched_file)
                    self._cr.commit()
                except Exception as e:
                    _logger.info(
                        "NZD Error While Fetch despatch  error = {}".format(e))
            self._cr.commit()
            sftp_client.close()

    def nzd_validate_delivery_orders(self):
        pickings = self.env['stock.picking'].search(
            [('state', 'not in', ['done', 'cancel']), ('name_3pl', '=', 'NZD'),
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

    def create_nzd_shipping_method(self, picking, carrier_3pl):
        delivery_carrier_obj = self.env['delivery.carrier']
        if carrier_3pl:
            delivery_carrier = delivery_carrier_obj.search(
                [('name', '=', carrier_3pl)], limit=1)
            if delivery_carrier:
                picking.carrier_id = delivery_carrier.id
            else:
                delivery_carrier = delivery_carrier_obj.create({
                    'name': carrier_3pl,
                    'product_id': self.env.ref('nzd_odoo_integration.nzd_shipping_product').id,
                    'delivery_type': 'fixed'
                })
                picking.carrier_id = delivery_carrier.id

    def purchase_order_despatch_report_fetch(self):
        sftp_server_id = self.env['sftp.syncing'].search(
            [('store', '=', 'nzd')], limit=1)
        if sftp_server_id:
            sftp_client = sftp_server_id.connect_sftp()
            matched_files = sftp_server_id.get_all_files_and_folders_from_server_location(sftp_client,
                                                                                          sftp_server_id.nzd_import_despatch_details_of_order_path,
                                                                                          match='.VCi')
            server_dir = sftp_client.getcwd()
            if server_dir[-1] != '/':
                server_dir += '/'
            matched_files = matched_files[:2]
            for matched_file in matched_files:
                sftp_server_id.import_file_to_local_from_sftp(sftp_client, server_dir + matched_file,
                                                              '/tmp/' + matched_file)
            for matched_file in matched_files:
                try:
                    reader = (open('/tmp/' + matched_file))
                    order = False
                    picking_ids = False
                    for data in reader:
                        data = data.split(',')
                        if data[0] == 'GIAH':
                            order = self.env['purchase.order'].search(
                                [('name', '=', data[2])], limit=1)

                            picking_ids = order.picking_ids.filtered(
                                lambda x: x.state not in ['done', 'cancel'])
                            if picking_ids:
                                date_of_shipped = datetime.strptime(
                                    str(data[4]), "%d-%m-%Y").date()
                                nzd_carrier = data[5]
                        if order and picking_ids and data[0] == 'GIAL':
                            for picking in picking_ids:
                                move_lines = picking.move_ids.filtered(
                                    lambda x: x.product_id.default_code == data[4] and not x.done_qty_3pl)
                                add_done_qty_3pl = False
                                if not move_lines:
                                    move_lines = picking.move_ids.filtered(
                                        lambda x: x.product_id.default_code == data[4] and x.done_qty_3pl)
                                    add_done_qty_3pl = True
                                if move_lines:
                                    picking.date_of_shipped = date_of_shipped
                                    if add_done_qty_3pl:
                                        move_lines[0].done_qty_3pl += float(
                                            data[6])
                                    else:
                                        move_lines[0].done_qty_3pl = float(
                                            data[6])
                                    self.create_nzd_shipping_method(
                                        picking, nzd_carrier)
                                    picking.name_3pl = 'NZD'
                                    picking.nzd_delivery_validate = False

                    order.nzd_purchase_order_processed = True
                    sftp_server_id.rename_file_from_sftp_server(sftp_client, server_dir + matched_file,
                                                                server_dir + '/Archive/' + matched_file)

                    self._cr.commit()
                except Exception as e:
                    _logger.info(
                        "NZD Error While Fetch despatch  error = {}".format(e))
            self._cr.commit()
            sftp_client.close()

    def nzd_validate_purchase_orders(self):
        pickings = self.env['stock.picking'].search(
            [('state', 'not in', ['done', 'cancel']), ('name_3pl', '=', 'NZD'),
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
