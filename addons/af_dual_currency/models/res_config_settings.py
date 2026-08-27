# Part of af_dual_currency. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    af_secondary_currency_id = fields.Many2one(
        related="company_id.af_secondary_currency_id", readonly=False,
    )
    af_show_secondary_on_documents = fields.Boolean(
        related="company_id.af_show_secondary_on_documents", readonly=False,
    )
