# Part of hm_timesheet. See LICENSE file for full copyright and licensing details.
"""Which day the working week starts on.

Saturday by default, because that is the Afghan working week and the whole
catalogue assumes it. Every other market gets to say otherwise, which costs
one selection field and saves the module from being unsellable outside
Afghanistan.

The values are Odoo's own: ISO weekday numbers, 1 for Monday through 7 for
Sunday, the same convention ``res.lang.week_start`` uses.
"""

from odoo import fields, models

WEEK_DAYS = [
    ("1", "Monday"),
    ("2", "Tuesday"),
    ("3", "Wednesday"),
    ("4", "Thursday"),
    ("5", "Friday"),
    ("6", "Saturday"),
    ("7", "Sunday"),
]


class ResCompany(models.Model):
    _inherit = "res.company"

    hm_timesheet_week_start = fields.Selection(
        selection=WEEK_DAYS,
        string="Timesheet Week Starts",
        default="6",
        help="The first day of a timesheet week. Saturday in Afghanistan.",
    )


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    hm_timesheet_week_start = fields.Selection(
        related="company_id.hm_timesheet_week_start",
        readonly=False,
        string="Timesheet Week Starts",
    )
