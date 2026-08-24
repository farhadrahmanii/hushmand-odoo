# Part of af_jalali. See LICENSE file for full copyright and licensing details.
"""Tests for the Odoo-facing service model."""

import datetime

from odoo.tests import common, tagged


@tagged("post_install", "-at_install")
class TestJalaliService(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.service = cls.env["af.jalali"]
        cls.company = cls.env.company
        cls.company.write({
            "jalali_enabled": True,
            "jalali_scheme": "afghan",
            "jalali_date_format": "yyyy/MM/dd",
            "jalali_eastern_digits": False,
        })
        cls.env.user.write({"jalali_calendar": "company", "lang": "en_US"})

    # ------------------------------------------------------------------
    # Settings resolution
    # ------------------------------------------------------------------

    def test_company_setting_applies(self):
        self.assertTrue(self.service.calendar_settings()["enabled"])
        self.company.jalali_enabled = False
        self.assertFalse(self.service.calendar_settings()["enabled"])

    def test_user_preference_overrides_company(self):
        """One accountant on Gregorian while the office reads Jalali."""
        self.company.jalali_enabled = True
        self.env.user.jalali_calendar = "gregorian"
        self.assertFalse(self.service.calendar_settings()["enabled"])

        self.company.jalali_enabled = False
        self.env.user.jalali_calendar = "jalali"
        self.assertTrue(self.service.calendar_settings()["enabled"])

    def test_user_can_edit_own_preference(self):
        """The field must be writable without write access on res.users."""
        self.assertIn("jalali_calendar", self.env.user.SELF_WRITEABLE_FIELDS)
        self.assertIn("jalali_calendar", self.env.user.SELF_READABLE_FIELDS)

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def test_format_date(self):
        result = self.service.format_date(datetime.date(2026, 8, 24))
        self.assertEqual(result, "1405/06/02")

    def test_format_date_accepts_string(self):
        self.assertEqual(self.service.format_date("2026-08-24"), "1405/06/02")

    def test_format_falls_back_when_disabled(self):
        self.company.jalali_enabled = False
        self.env.user.jalali_calendar = "company"
        self.assertEqual(self.service.format_date("2026-08-24"), "2026-08-24")

    def test_force_formats_even_when_disabled(self):
        """Reports opt in explicitly, so printing is not silently Gregorian."""
        self.company.jalali_enabled = False
        self.env.user.jalali_calendar = "company"
        self.assertEqual(
            self.service.format_date("2026-08-24", force=True), "1405/06/02"
        )

    def test_empty_values(self):
        self.assertEqual(self.service.format_date(False), "")
        self.assertEqual(self.service.format_date(None), "")
        self.assertEqual(self.service.format_datetime(False), "")

    def test_bad_value_does_not_raise(self):
        """A malformed value must not break a whole list view."""
        self.assertEqual(self.service.format_date("not-a-date"), "")

    def test_custom_company_format(self):
        self.company.jalali_date_format = "dd MMMM yyyy"
        self.assertEqual(
            self.service.format_date("2026-08-24"), "02 Sunbula 1405"
        )

    def test_eastern_digits_setting(self):
        self.company.jalali_eastern_digits = True
        self.assertEqual(self.service.format_date("2026-08-24"), "۱۴۰۵/۰۶/۰۲")

    def test_scheme_setting(self):
        self.company.jalali_date_format = "MMMM"
        self.company.jalali_scheme = "iranian"
        self.assertEqual(self.service.format_date("2026-08-24"), "Shahrivar")

    # ------------------------------------------------------------------
    # Timezone
    # ------------------------------------------------------------------

    def test_datetime_uses_user_timezone(self):
        """22:00 UTC is already the next day in Kabul (UTC+4:30)."""
        self.env.user.tz = "Asia/Kabul"
        service = self.env["af.jalali"].with_user(self.env.user)
        late = datetime.datetime(2026, 8, 24, 22, 0, 0)
        self.assertEqual(
            service.format_datetime(late, fmt="yyyy/MM/dd"), "1405/06/03"
        )

    def test_datetime_without_conversion(self):
        self.env.user.tz = "Asia/Kabul"
        late = datetime.datetime(2026, 8, 24, 22, 0, 0)
        self.assertEqual(
            self.service.format_datetime(late, fmt="yyyy/MM/dd", tz_convert=False),
            "1405/06/02",
        )

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def test_parse(self):
        self.assertEqual(self.service.parse("1405/06/02"), datetime.date(2026, 8, 24))

    def test_try_parse_returns_none(self):
        self.assertIsNone(self.service.try_parse("nonsense"))
        self.assertIsNone(self.service.try_parse(""))

    # ------------------------------------------------------------------
    # Client payload
    # ------------------------------------------------------------------

    def test_client_settings_payload(self):
        payload = self.service.client_settings()
        for key in ("enabled", "scheme", "lang", "eastern_digits",
                    "date_format", "datetime_format",
                    "month_names", "weekday_names"):
            self.assertIn(key, payload)
        self.assertEqual(len(payload["month_names"]), 12)
        self.assertEqual(len(payload["weekday_names"]), 7)
        self.assertEqual(payload["weekday_names"][0], "Shanbe")

    def test_today(self):
        self.assertEqual(len(self.service.today()), 3)


@tagged("post_install", "-at_install")
class TestQwebWidgets(common.TransactionCase):
    """The report path: t-options='{"widget": "jalali"}'."""

    def test_date_widget_renders(self):
        converter = self.env["ir.qweb.field.jalali"]
        self.assertEqual(
            converter.value_to_html(datetime.date(2026, 8, 24), {}), "1405/06/02"
        )

    def test_date_widget_honours_format_option(self):
        converter = self.env["ir.qweb.field.jalali"]
        self.assertEqual(
            converter.value_to_html(
                datetime.date(2026, 8, 24), {"format": "dd MMMM yyyy"}
            ),
            "02 Sunbula 1405",
        )

    def test_widget_empty_value(self):
        self.assertEqual(self.env["ir.qweb.field.jalali"].value_to_html(False, {}), "")
