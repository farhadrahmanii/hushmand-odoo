# Part of af_jalali. See LICENSE file for full copyright and licensing details.
"""The service model every other module talks to.

TIER 1 -- this is the only place that bridges Odoo and the pure-Python core.
It deliberately uses nothing but long-stable ORM APIs (``models.AbstractModel``,
``api.model``, ``fields.Datetime.context_timestamp``) so that porting to a new
Odoo release touches the UI layer, not this file.

Usage from any other module::

    self.env['af.jalali'].format_date(record.date_start)
    self.env['af.jalali'].parse('1405/06/02')
"""

import datetime
import logging

from odoo import api, fields, models

from ..core import formats, jalali

_logger = logging.getLogger(__name__)


class JalaliService(models.AbstractModel):
    _name = "af.jalali"
    _description = "Jalali Calendar Service"

    # ------------------------------------------------------------------
    # Settings resolution
    # ------------------------------------------------------------------

    @api.model
    def calendar_settings(self):
        """Effective calendar settings for the current user and company.

        The user preference wins over the company default, so one accountant
        can stay on Gregorian while the rest of the office reads Jalali.

        :return: dict with ``enabled``, ``scheme``, ``lang``, ``eastern_digits``,
            ``date_format`` and ``datetime_format``.
        """
        user = self.env.user
        company = self.env.company

        preference = user.jalali_calendar or "company"
        if preference == "jalali":
            enabled = True
        elif preference == "gregorian":
            enabled = False
        else:
            enabled = bool(company.jalali_enabled)

        lang = (user.lang or self.env.context.get("lang") or "en_US").split("_")[0]

        return {
            "enabled": enabled,
            "scheme": company.jalali_scheme or formats.SCHEME_AFGHAN,
            "lang": lang,
            "eastern_digits": bool(company.jalali_eastern_digits),
            "date_format": company.jalali_date_format or formats.DEFAULT_FORMAT,
            "datetime_format": company.jalali_datetime_format or "yyyy/MM/dd HH:mm",
        }

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    @api.model
    def format_date(self, value, fmt=None, force=False):
        """Format a date as Jalali text.

        :param value: ``date``, ``datetime`` or an Odoo date string.
        :param fmt: pattern override, see :func:`core.formats.format_jalali`.
        :param force: format even when the calendar is switched off.
        :return: formatted string, or ``''`` for a falsy value.
        """
        value = self._coerce_date(value)
        if not value:
            return ""

        settings = self.calendar_settings()
        if not settings["enabled"] and not force:
            return fields.Date.to_string(value)

        return formats.format_jalali(
            value,
            fmt or settings["date_format"],
            scheme=settings["scheme"],
            lang=settings["lang"],
            eastern_digits=settings["eastern_digits"],
        )

    @api.model
    def format_datetime(self, value, fmt=None, force=False, tz_convert=True):
        """Format a datetime as Jalali text.

        Odoo stores datetimes in UTC, so they are converted to the user's
        timezone first -- otherwise an evening entry in Kabul shows up on the
        previous day.
        """
        value = self._coerce_datetime(value)
        if not value:
            return ""

        if tz_convert:
            value = fields.Datetime.context_timestamp(self, value)

        settings = self.calendar_settings()
        if not settings["enabled"] and not force:
            return fields.Datetime.to_string(value)

        return formats.format_jalali(
            value,
            fmt or settings["datetime_format"],
            scheme=settings["scheme"],
            lang=settings["lang"],
            eastern_digits=settings["eastern_digits"],
        )

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    @api.model
    def parse(self, text):
        """Parse Jalali text into a :class:`datetime.date`.

        :raises ValueError: if the text is not a valid Jalali date.
        """
        settings = self.calendar_settings()
        return formats.parse_jalali(
            text, scheme=settings["scheme"], lang=settings["lang"]
        )

    @api.model
    def try_parse(self, text):
        """Like :meth:`parse` but returns ``None`` instead of raising."""
        try:
            return self.parse(text)
        except (ValueError, TypeError):
            return None

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @api.model
    def today(self):
        """Today's date in the user's timezone, as a Jalali ``(y, m, d)``."""
        return jalali.date_to_jalali(fields.Date.context_today(self))

    @api.model
    def month_names(self, scheme=None, lang=None):
        """The twelve month names, for selection fields and pickers."""
        settings = self.calendar_settings()
        return [
            formats.month_name(m, scheme or settings["scheme"], lang or settings["lang"])
            for m in range(1, 13)
        ]

    @api.model
    def weekday_names(self, lang=None):
        """The seven weekday names, Saturday first."""
        settings = self.calendar_settings()
        return list(formats.WEEKDAY_NAMES.get(lang or settings["lang"],
                                              formats.WEEKDAY_NAMES["en"]))

    @api.model
    def client_settings(self):
        """Everything the browser needs to render Jalali without a round trip."""
        settings = self.calendar_settings()
        settings["month_names"] = self.month_names()
        settings["weekday_names"] = self.weekday_names()
        return settings

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @api.model
    def _coerce_date(self, value):
        """Accept a date, datetime or Odoo date string; return a date."""
        if not value:
            return None
        if isinstance(value, datetime.datetime):
            return value.date()
        if isinstance(value, datetime.date):
            return value
        try:
            return fields.Date.to_date(value)
        except (ValueError, TypeError):
            _logger.warning("af_jalali: cannot coerce %r to a date", value)
            return None

    @api.model
    def _coerce_datetime(self, value):
        """Accept a datetime or Odoo datetime string; return a datetime."""
        if not value:
            return None
        if isinstance(value, datetime.datetime):
            return value
        if isinstance(value, datetime.date):
            return datetime.datetime.combine(value, datetime.time.min)
        try:
            return fields.Datetime.to_datetime(value)
        except (ValueError, TypeError):
            _logger.warning("af_jalali: cannot coerce %r to a datetime", value)
            return None
