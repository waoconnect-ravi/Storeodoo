
from odoo import fields, models
from odoo.exceptions import ValidationError


class ExportProductNZd(models.TransientModel):
    _name = 'export.product.nzd'

    def _set_sftp_server_id(self):
        sftp_server_id = self.env['sftp.syncing'].search(
            [('store', '=', 'nzd')], limit=1)
        if sftp_server_id:
            return sftp_server_id.id
        return False

    sftp_server_id = fields.Many2one(
        'sftp.syncing', string="SFTP Server", default=_set_sftp_server_id)

    def export_product_in_nzd(self):
        try:
            product_obj = self.env['product.product']
            products = product_obj.browse(self.env.context.get('active_ids'))
            if products:
                product_obj.export_product_to_nzd(
                    products.ids, self.sftp_server_id.id)
        except Exception as e:
            raise ValidationError("Export Product Error : {}".format(e))
