# Part of af_jalali. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    jalali_calendar = fields.Selection(
        selection=[
            ("company", "Follow company setting"),
            ("jalali", "Always Jalali"),
            ("gregorian", "Always Gregorian"),
        ],
        string="Calendar",
        default="company",
        required=True,
        help="Which calendar this user sees. Overrides the company default, so "
             "staff working with foreign partners can stay on Gregorian.",
    )

    # A user must be able to change their own calendar from Preferences without
    # holding write access on res.users. These two properties are the supported
    # way to whitelist a field for that -- one of the few places in this module
    # that is worth re-checking when porting to a new Odoo release.
    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["jalali_calendar"]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["jalali_calendar"]
