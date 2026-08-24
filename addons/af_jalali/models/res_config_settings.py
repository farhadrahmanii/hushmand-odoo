# Part of af_jalali. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    jalali_enabled = fields.Boolean(
        related="company_id.jalali_enabled", readonly=False,
    )
    jalali_scheme = fields.Selection(
        related="company_id.jalali_scheme", readonly=False,
    )
    jalali_eastern_digits = fields.Boolean(
        related="company_id.jalali_eastern_digits", readonly=False,
    )
    jalali_date_format = fields.Char(
        related="company_id.jalali_date_format", readonly=False,
    )
    jalali_datetime_format = fields.Char(
        related="company_id.jalali_datetime_format", readonly=False,
    )
