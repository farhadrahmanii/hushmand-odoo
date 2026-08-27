# Part of af_dual_currency. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    af_secondary_currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Second Currency",
        help="A second currency to show amounts in alongside the company "
             "currency, normally AFN. Rates come from exchange periods, not "
             "from the daily rate table.",
    )
    af_show_secondary_on_documents = fields.Boolean(
        string="Show on Documents",
        default=True,
        help="Show the second-currency total on invoices and bills.",
    )
