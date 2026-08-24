# Part of af_jalali. See LICENSE file for full copyright and licensing details.
"""QWeb field widgets, so any report can print Jalali without extra code.

In a report template::

    <span t-field="doc.date_order" t-options='{"widget": "jalali"}'/>
    <span t-field="doc.create_date" t-options='{"widget": "jalali_datetime"}'/>

An optional pattern can be passed too::

    <span t-field="doc.date_order"
          t-options='{"widget": "jalali", "format": "EEEE, dd MMMM yyyy"}'/>

Registering a widget by declaring ``ir.qweb.field.<name>`` has been the stable
mechanism for many Odoo releases, which is why it is preferred here over
touching the renderer.
"""

from odoo import api, models


class JalaliDateConverter(models.AbstractModel):
    _name = "ir.qweb.field.jalali"
    _inherit = "ir.qweb.field.date"
    _description = "Jalali Date Field Converter"

    @api.model
    def value_to_html(self, value, options):
        if not value:
            return ""
        return self.env["af.jalali"].format_date(
            value,
            fmt=(options or {}).get("format"),
            force=(options or {}).get("force", True),
        )


class JalaliDatetimeConverter(models.AbstractModel):
    _name = "ir.qweb.field.jalali_datetime"
    _inherit = "ir.qweb.field.datetime"
    _description = "Jalali Datetime Field Converter"

    @api.model
    def value_to_html(self, value, options):
        if not value:
            return ""
        options = options or {}
        return self.env["af.jalali"].format_datetime(
            value,
            fmt=options.get("format"),
            force=options.get("force", True),
            tz_convert=options.get("tz_convert", True),
        )
