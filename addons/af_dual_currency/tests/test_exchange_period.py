# Part of af_dual_currency. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.exceptions import UserError, ValidationError
from odoo.tests import common, tagged


@tagged("post_install", "-at_install")
class TestExchangePeriod(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.afn = cls.env.ref("base.AFN")
        cls.afn.active = True
        cls.company.af_secondary_currency_id = cls.afn
        cls.Period = cls.env["af.exchange.period"]

    def _make_period(self, name="2026-08", start="2026-08-01", end="2026-08-31",
                     rate=70.0):
        return self.Period.create({
            "name": name,
            "company_id": self.company.id,
            "currency_id": self.afn.id,
            "date_from": start,
            "date_to": end,
            "rate": rate,
        })

    # ------------------------------------------------------------------
    # The core promise: a rate that stops changing
    # ------------------------------------------------------------------

    def test_closed_period_rejects_rate_change(self):
        """The whole reason this model exists. Editing a rate after the month
        has been reported changes figures that have already left the office."""
        period = self._make_period()
        period.action_confirm()
        period.action_close()

        with self.assertRaises(UserError):
            period.rate = 75.0

    def test_closed_period_rejects_date_change(self):
        period = self._make_period()
        period.action_confirm()
        period.action_close()
        with self.assertRaises(UserError):
            period.date_to = "2026-09-15"

    def test_closed_period_allows_notes(self):
        """Locking the rate must not stop someone recording why."""
        period = self._make_period()
        period.action_confirm()
        period.action_close()
        period.note = "Central bank reference, 1 Sunbula"
        self.assertTrue(period.note)

    def test_closed_period_cannot_be_deleted(self):
        period = self._make_period()
        period.action_confirm()
        period.action_close()
        with self.assertRaises(UserError):
            period.unlink()

    def test_reopen_then_edit(self):
        period = self._make_period()
        period.action_confirm()
        period.action_close()
        period.action_reopen()
        period.rate = 75.0
        self.assertEqual(period.rate, 75.0)

    # ------------------------------------------------------------------
    # Publishing to Odoo's own rate table
    # ------------------------------------------------------------------

    def test_confirm_publishes_an_odoo_rate(self):
        """Confirming must feed Odoo's mechanism, not bypass it, or invoices
        and accounting would disagree with the period."""
        period = self._make_period()
        self.assertFalse(period.rate_id)

        period.action_confirm()

        self.assertTrue(period.rate_id)
        self.assertEqual(period.rate_id.currency_id, self.afn)
        self.assertEqual(period.rate_id.name, date(2026, 8, 1))
        self.assertAlmostEqual(period.rate_id.rate, 70.0, places=6)

    def test_rate_lands_on_the_root_company(self):
        """Odoo's own default puts rates on the root company; anything else
        and a multi-company setup stops finding them."""
        period = self._make_period()
        period.action_confirm()
        self.assertEqual(
            period.rate_id.company_id, self.company.root_id or self.company
        )

    def test_confirm_reuses_a_rate_already_on_that_date(self):
        """Only one rate per currency per day is allowed, so a period must
        adopt an existing rate rather than collide with it."""
        existing = self.env["res.currency.rate"].create({
            "name": "2026-08-01",
            "currency_id": self.afn.id,
            "company_id": (self.company.root_id or self.company).id,
            "rate": 65.0,
        })
        period = self._make_period()
        period.action_confirm()

        self.assertEqual(period.rate_id, existing)
        self.assertAlmostEqual(existing.rate, 70.0, places=6)

    def test_reset_to_draft_withdraws_the_rate(self):
        period = self._make_period()
        period.action_confirm()
        rate = period.rate_id
        period.action_reset_draft()
        self.assertEqual(period.state, "draft")
        self.assertFalse(rate.exists())

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------

    def test_cannot_close_a_draft(self):
        with self.assertRaises(UserError):
            self._make_period().action_close()

    def test_cannot_confirm_twice(self):
        period = self._make_period()
        period.action_confirm()
        with self.assertRaises(UserError):
            period.action_confirm()

    def test_cannot_reopen_something_not_closed(self):
        period = self._make_period()
        period.action_confirm()
        with self.assertRaises(UserError):
            period.action_reopen()

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------

    def test_overlapping_periods_rejected(self):
        """Two periods covering one day would make the rate ambiguous."""
        self._make_period()
        with self.assertRaises(ValidationError):
            self._make_period(
                name="overlap", start="2026-08-15", end="2026-09-15"
            )

    def test_adjacent_periods_allowed(self):
        self._make_period()
        september = self._make_period(
            name="2026-09", start="2026-09-01", end="2026-09-30", rate=71.0
        )
        self.assertTrue(september)

    def test_second_currency_must_differ(self):
        with self.assertRaises(ValidationError):
            self.Period.create({
                "name": "bad",
                "company_id": self.company.id,
                "currency_id": self.company.currency_id.id,
                "date_from": "2027-01-01",
                "date_to": "2027-01-31",
                "rate": 1.0,
            })

    # ------------------------------------------------------------------
    # Conversion helpers
    # ------------------------------------------------------------------

    def test_convert_uses_the_period_rate(self):
        period = self._make_period()
        period.action_confirm()
        amount, used = self.Period._convert(100.0, date(2026, 8, 15))
        self.assertAlmostEqual(amount, 7000.0, places=2)
        self.assertEqual(used, period)

    def test_convert_ignores_a_draft_period(self):
        """An unconfirmed rate is a proposal, not something to report on."""
        self._make_period()
        amount, used = self.Period._convert(100.0, date(2026, 8, 15))
        self.assertEqual(amount, 0.0)
        self.assertFalse(used)

    def test_convert_without_a_period_returns_zero_not_a_guess(self):
        """Zero makes a missing rate visible. Falling back to Odoo's daily
        rate would produce a plausible number that nobody agreed to."""
        amount, used = self.Period._convert(100.0, date(2030, 1, 1))
        self.assertEqual(amount, 0.0)
        self.assertFalse(used)

    def test_convert_with_no_date(self):
        amount, used = self.Period._convert(100.0, False)
        self.assertEqual(amount, 0.0)
        self.assertFalse(used)

    def test_period_lookup_at_boundaries(self):
        period = self._make_period()
        period.action_confirm()
        for day in (date(2026, 8, 1), date(2026, 8, 31)):
            with self.subTest(day=day):
                self.assertEqual(self.Period._period_for(day), period)
        self.assertFalse(self.Period._period_for(date(2026, 7, 31)))
        self.assertFalse(self.Period._period_for(date(2026, 9, 1)))

    def test_inverse_rate(self):
        """The field is declared at six decimals, so the check matches that
        rather than full float precision."""
        period = self._make_period(rate=70.0)
        self.assertAlmostEqual(period.inverse_rate, round(1 / 70.0, 6), places=6)

    def test_inverse_rate_of_zero_does_not_divide(self):
        period = self._make_period(rate=70.0)
        period.rate = 0.000001
        self.assertGreater(period.inverse_rate, 0)

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def test_create_monthly_periods(self):
        periods = self.Period.create_monthly_periods(2027, 72.0)
        self.assertEqual(len(periods), 12)
        self.assertEqual(periods[0].date_from, date(2027, 1, 1))
        self.assertEqual(
            periods.filtered(lambda p: p.name == "2027-02").date_to,
            date(2027, 2, 28),
        )
        self.assertTrue(all(p.state == "draft" for p in periods))

    def test_monthly_periods_do_not_overlap(self):
        periods = self.Period.create_monthly_periods(2028, 72.0)
        self.assertEqual(len(periods), 12)
        # A leap year: February must end on the 29th.
        february = periods.filtered(lambda p: p.name == "2028-02")
        self.assertEqual(february.date_to, date(2028, 2, 29))
