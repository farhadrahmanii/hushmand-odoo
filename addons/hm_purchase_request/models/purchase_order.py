# Part of hm_purchase_request. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    hm_request_id = fields.Many2one(
        comodel_name="hm.purchase.request",
        string="Purchase Request",
        readonly=True,
        index="btree_not_null",
        help="The approved request this order came from.",
    )
