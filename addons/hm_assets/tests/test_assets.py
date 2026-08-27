# Part of hm_assets. See LICENSE file for full copyright and licensing details.
"""Tests for fixed assets.

The assertions that matter are arithmetic and irreversibility: a schedule that
adds up to exactly the depreciable value, and posted periods that cannot be
edited or deleted afterwards.
"""

from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestAssets(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.journal = cls.env["account.journal"].search(
            [("type", "=", "general"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        cls.account_asset = cls._account("ASSET1", "asset_fixed")
        cls.account_depreciation = cls._account("ASSET2", "asset_fixed")
        cls.account_expense = cls._account("EXPDEP", "expense_depreciation")

    @classmethod
    def _account(cls, code, account_type):
        return cls.env["account.account"].create({
            "name": code,
            "code": code,
            "account_type": account_type,
        })

    def _asset(self, **values):
        data = {
            "name": "Test Vehicle",
            "purchase_value": 10000.0,
            "salvage_value": 0.0,
            "date_start": "2026-01-01",
            "method": "linear",
            "period_length": "12",
            "period_count": 5,
            "prorata": False,
            "account_asset_id": self.account_asset.id,
            "account_depreciation_id": self.account_depreciation.id,
            "account_expense_id": self.account_expense.id,
            "journal_id": self.journal.id,
        }
        data.update(values)
        return self.env["hm.asset"].create(data)

    # ------------------------------------------------------------------
    # The schedule adds up
    # ------------------------------------------------------------------

    def test_linear_schedule_totals_the_depreciable_value(self):
        """The single most important property: depreciate exactly the value,
        no more and no less."""
        asset = self._asset()
        asset.action_compute_depreciation()

        self.assertEqual(len(asset.line_ids), 5)
        total = sum(asset.line_ids.mapped("amount"))
        self.assertAlmostEqual(total, 10000.0, places=2)

    def test_linear_periods_are_equal(self):
        asset = self._asset()
        asset.action_compute_depreciation()
        amounts = asset.line_ids.mapped("amount")
        self.assertTrue(all(abs(a - 2000.0) < 0.01 for a in amounts))

    def test_salvage_value_is_never_depreciated(self):
        asset = self._asset(salvage_value=1000.0)
        asset.action_compute_depreciation()
        total = sum(asset.line_ids.mapped("amount"))
        self.assertAlmostEqual(total, 9000.0, places=2)
        self.assertAlmostEqual(
            asset.line_ids.sorted("sequence")[-1].remaining_value,
            1000.0, places=2,
        )

    def test_degressive_writes_off_more_early(self):
        asset = self._asset(method="degressive", method_progress_factor=0.4)
        asset.action_compute_depreciation()
        lines = asset.line_ids.sorted("sequence")
        self.assertGreater(lines[0].amount, lines[1].amount)

    def test_degressive_still_totals_exactly(self):
        """A reducing balance never reaches zero on its own, so the last
        period has to absorb the remainder."""
        asset = self._asset(method="degressive", method_progress_factor=0.3)
        asset.action_compute_depreciation()
        total = sum(asset.line_ids.mapped("amount"))
        self.assertAlmostEqual(total, 10000.0, places=2)

    def test_rounding_does_not_leak(self):
        """A value that does not divide evenly must still total exactly."""
        asset = self._asset(purchase_value=10000.0, period_count=3)
        asset.action_compute_depreciation()
        total = sum(asset.line_ids.mapped("amount"))
        self.assertAlmostEqual(total, 10000.0, places=2)

    def test_prorata_reduces_the_first_period(self):
        """An asset in service from July should not be charged a full year."""
        full = self._asset(prorata=False, date_start="2026-07-01")
        full.action_compute_depreciation()
        prorated = self._asset(prorata=True, date_start="2026-07-01")
        prorated.action_compute_depreciation()

        self.assertLess(
            prorated.line_ids.sorted("sequence")[0].amount,
            full.line_ids.sorted("sequence")[0].amount,
        )

    def test_prorata_is_roughly_the_days_in_service(self):
        """July to December is a little over half a calendar year."""
        asset = self._asset(prorata=True, date_start="2026-07-01")
        asset.action_compute_depreciation()
        first = asset.line_ids.sorted("sequence")[0].amount
        self.assertGreater(first, 900.0)
        self.assertLess(first, 1100.0)

    def test_prorata_on_the_first_day_of_the_year_charges_a_full_period(self):
        asset = self._asset(prorata=True, date_start="2026-01-01")
        asset.action_compute_depreciation()
        self.assertAlmostEqual(
            asset.line_ids.sorted("sequence")[0].amount, 2000.0, places=2
        )

    def test_periods_align_to_the_calendar(self):
        """A yearly asset in service in July still ends its first period on
        31 December, because a register is read against the company's periods
        rather than each asset's anniversary."""
        asset = self._asset(date_start="2026-07-01")
        asset.action_compute_depreciation()
        first = asset.line_ids.sorted("sequence")[0]
        self.assertEqual(first.date.month, 12)
        self.assertEqual(first.date.day, 31)
        self.assertEqual(first.date.year, 2026)

    # ------------------------------------------------------------------
    # Posting
    # ------------------------------------------------------------------

    def test_posting_creates_a_balanced_entry(self):
        asset = self._asset()
        asset.action_confirm()
        line = asset.line_ids.sorted("sequence")[0]
        line.action_post()

        self.assertTrue(line.posted)
        move = line.move_id
        self.assertTrue(move)
        self.assertAlmostEqual(
            sum(move.line_ids.mapped("debit")),
            sum(move.line_ids.mapped("credit")),
            places=2,
        )

    def test_entry_debits_expense_and_credits_depreciation(self):
        asset = self._asset()
        asset.action_confirm()
        line = asset.line_ids.sorted("sequence")[0]
        line.action_post()

        debit = line.move_id.line_ids.filtered(lambda l: l.debit > 0)
        credit = line.move_id.line_ids.filtered(lambda l: l.credit > 0)
        self.assertEqual(debit.account_id, self.account_expense)
        self.assertEqual(credit.account_id, self.account_depreciation)

    def test_book_value_falls_as_periods_post(self):
        asset = self._asset()
        asset.action_confirm()
        self.assertAlmostEqual(asset.book_value, 10000.0, places=2)

        asset.line_ids.sorted("sequence")[0].action_post()
        asset.invalidate_recordset(["book_value", "depreciated_value"])
        self.assertAlmostEqual(asset.book_value, 8000.0, places=2)

    def test_cannot_post_twice(self):
        asset = self._asset()
        asset.action_confirm()
        line = asset.line_ids.sorted("sequence")[0]
        line.action_post()
        with self.assertRaises(UserError):
            line.action_post()

    def test_cannot_post_on_a_draft_asset(self):
        asset = self._asset()
        asset.action_compute_depreciation()
        with self.assertRaises(UserError):
            asset.line_ids.sorted("sequence")[0].action_post()

    # ------------------------------------------------------------------
    # Posted figures are not editable
    # ------------------------------------------------------------------

    def test_a_posted_period_cannot_be_edited(self):
        """Once a number is in the ledger it stops being this module's to
        change."""
        asset = self._asset()
        asset.action_confirm()
        line = asset.line_ids.sorted("sequence")[0]
        line.action_post()
        with self.assertRaises(UserError):
            line.amount = 500.0

    def test_a_posted_period_cannot_be_deleted(self):
        asset = self._asset()
        asset.action_confirm()
        line = asset.line_ids.sorted("sequence")[0]
        line.action_post()
        with self.assertRaises(UserError):
            line.unlink()

    def test_recomputing_keeps_posted_periods(self):
        asset = self._asset()
        asset.action_confirm()
        first = asset.line_ids.sorted("sequence")[0]
        first.action_post()

        asset.action_compute_depreciation()
        self.assertIn(first, asset.line_ids)
        self.assertTrue(first.posted)

    def test_recomputing_only_schedules_what_is_left(self):
        asset = self._asset()
        asset.action_confirm()
        asset.line_ids.sorted("sequence")[0].action_post()
        asset.action_compute_depreciation()

        unposted = asset.line_ids.filtered(lambda l: not l.posted)
        self.assertAlmostEqual(sum(unposted.mapped("amount")), 8000.0, places=2)

    def test_cannot_cancel_once_something_is_posted(self):
        asset = self._asset()
        asset.action_confirm()
        asset.line_ids.sorted("sequence")[0].action_post()
        with self.assertRaises(UserError):
            asset.action_cancel()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def test_confirm_requires_accounts(self):
        asset = self._asset(account_expense_id=False)
        with self.assertRaises(UserError):
            asset.action_confirm()

    def test_closing_drops_unposted_periods_only(self):
        asset = self._asset()
        asset.action_confirm()
        asset.line_ids.sorted("sequence")[0].action_post()
        asset.action_close()

        self.assertEqual(asset.state, "closed")
        self.assertEqual(len(asset.line_ids), 1)
        self.assertTrue(asset.line_ids.posted)
        self.assertTrue(asset.date_disposal)

    def test_post_due_ignores_future_periods(self):
        asset = self._asset(date_start="2020-01-01", period_count=10)
        asset.action_confirm()
        asset.line_ids.action_post_due()

        today = fields.Date.context_today(asset)
        posted = asset.line_ids.filtered("posted")
        self.assertTrue(posted, "nothing was due, so the test proves nothing")
        for line in asset.line_ids:
            if line.date <= today:
                self.assertTrue(line.posted, "a due period was skipped")
            else:
                self.assertFalse(line.posted, "a future period was posted")

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def test_salvage_cannot_exceed_purchase(self):
        with self.assertRaises(ValidationError):
            self._asset(salvage_value=20000.0)

    def test_degressive_factor_must_be_a_fraction(self):
        with self.assertRaises(ValidationError):
            self._asset(method="degressive", method_progress_factor=1.5)

    def test_category_supplies_defaults(self):
        category = self.env["hm.asset.category"].create({
            "name": "Vehicles",
            "method": "degressive",
            "method_progress_factor": 0.25,
            "period_count": 8,
            "account_asset_id": self.account_asset.id,
            "account_depreciation_id": self.account_depreciation.id,
            "account_expense_id": self.account_expense.id,
            "journal_id": self.journal.id,
        })
        asset = self.env["hm.asset"].new({
            "name": "From category",
            "purchase_value": 5000.0,
            "category_id": category.id,
        })
        asset._onchange_category()
        self.assertEqual(asset.method, "degressive")
        self.assertEqual(asset.period_count, 8)
        self.assertEqual(asset.account_expense_id, self.account_expense)
