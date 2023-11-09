
from odoo import fields, models
from odoo.exceptions import ValidationError


class ExportSaleOrderNZD(models.TransientModel):
    _name = 'export.sale.order.nzd'

    def _set_sftp_server_id(self):
        sftp_server_id = self.env['sftp.syncing'].search(
            [('store', '=', 'nzd')], limit=1)
        if sftp_server_id:
            return sftp_server_id.id
        return False

    sftp_server_id = fields.Many2one(
        'sftp.syncing', string="SFTP Server", default=_set_sftp_server_id)

    def export_sale_order_in_nzd(self):
        try:

            orders = self.env['sale.order'].browse(self.env.context.get(
                'active_ids')).filtered(lambda x: not x.send_order_to_nzd)
            if orders.filtered(lambda x: x.state not in ['sale', 'done']):
                raise ValidationError(
                    "This option is only used to export sales order which is confirmed or done.\nPlease Check your selected order list and remove order which is not confirmed or done.")
            for order in orders:
                sftp_server_id = self.env['sftp.syncing'].search(
                    [('store', '=', 'nzd'), ('warehouse_id', '=', order.warehouse_id.id)])
                if not sftp_server_id:
                    continue
                order.with_context(call_from_action=True).export_sale_order_file_in_nzd(
                    sftp_server_id.id)
        except Exception as e:
            raise ValidationError("Export Order Error : {}".format(e))
