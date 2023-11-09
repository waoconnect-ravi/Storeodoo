
from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    done_qty_3pl = fields.Float(string="3PL Done Qty", copy=False)
