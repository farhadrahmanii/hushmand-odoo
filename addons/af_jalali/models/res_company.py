# Part of af_jalali. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

from ..core import formats


class ResCompany(models.Model):
    _inherit = "res.company"

    jalali_enabled = fields.Boolean(
        string="Jalali Calendar",
        default=False,
        help="Show dates in the Jalali (Hijri-Shamsi) calendar throughout the "
             "interface and on printed documents. Dates are still stored as "
             "Gregorian, so nothing else in Odoo is affected.",
    )
    jalali_scheme = fields.Selection(
        selection=[
            (formats.SCHEME_AFGHAN, "Afghan (Hamal, Sawr, Jawza)"),
            (formats.SCHEME_IRANIAN, "Iranian (Farvardin, Ordibehesht, Khordad)"),
        ],
        string="Month Names",
        default=formats.SCHEME_AFGHAN,
        required=True,
        help="Afghanistan and Iran share the calendar but not the month names. "
             "Pick the naming your organisation uses.",
    )
    jalali_eastern_digits = fields.Boolean(
        string="Persian Digits",
        default=False,
        help="Display dates with Persian numerals instead of 0-9.",
    )
    jalali_date_format = fields.Char(
        string="Date Format",
        default=formats.DEFAULT_FORMAT,
        help="Pattern for dates. Tokens: yyyy, yy, MMMM, MMM, MM, M, dd, d, EEEE.",
    )
    jalali_datetime_format = fields.Char(
        string="Date and Time Format",
        default="yyyy/MM/dd HH:mm",
        help="Pattern for date and time values. Adds HH, mm and ss to the "
             "date tokens.",
    )
