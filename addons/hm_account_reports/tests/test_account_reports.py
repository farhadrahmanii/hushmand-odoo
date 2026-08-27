# Part of hm_account_reports. See LICENSE file for full copyright and licensing details.
"""Tests for the financial statements.

The assertions people actually care about are the arithmetic ones: a trial
balance whose debits equal its credits, and a balance sheet that balances. If
those hold on real posted entries, the statements can be handed to an auditor.
"""

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestFinancialReports(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.engine = cls.env["hm.account.report"]
        cls.Wizard = cls.env["hm.account.report.wizard"]

        # A posted invoice gives us income and a receivable; a posted bill
        # gives us an expense and a payable. That is enough for every
        # statement to have something on both sides.
        cls.invoice = cls.init_invoice(
            "out_invoice", invoice_date="2026-03-15", amounts=[1000.0], taxes=[]
        )
        cls.invoice.action_post()

        cls.bill = cls.init_invoice(
            "in_invoice", invoice_date="2026-03-20", amounts=[400.0], taxes=[]
        )
        cls.bill.action_post()

    def _wizard(self, report_type="trial_balance", **values):
        data = {
            "report_type": report_type,
            "date_from": "2026-01-01",
            "date_to": "2026-12-31",
            "company_ids": [(6, 0, self.env.company.ids)],
        }
        data.update(values)
        return self.Wizard.create(data)

    def _options(self, **values):
        return self._wizard(**values)._options()

    # ------------------------------------------------------------------
    # Trial balance
    # ------------------------------------------------------------------

    def test_trial_balance_debits_equal_credits(self):
        """The one check an accountant makes first."""
        result = self.engine.trial_balance(self._options())
        totals = result["totals"]
        self.assertAlmostEqual(totals["debit"], totals["credit"], places=2)
        self.assertGreater(totals["debit"], 0.0, "no entries were picked up")

    def test_trial_balance_closing_sums_to_zero(self):
        """Every closing balance together must net out, since each entry has
        both sides."""
        result = self.engine.trial_balance(self._options())
        self.assertAlmostEqual(result["totals"]["closing"], 0.0, places=2)

    def test_trial_balance_includes_the_invoice(self):
        result = self.engine.trial_balance(self._options())
        self.assertTrue(result["lines"])
        self.assertAlmostEqual(result["totals"]["debit"], 1400.0, places=2)

    def test_profit_and_loss_accounts_have_no_opening(self):
        """Income and expenses reset each year, so a brought-forward figure
        would be wrong."""
        options = self._options(date_from="2026-06-01")
        result = self.engine.trial_balance(options)
        for line in result["lines"]:
            if line["group"] in ("income", "expense"):
                self.assertEqual(
                    line["opening"], 0.0,
                    "%s should not carry an opening balance" % line["name"],
                )

    def test_balance_sheet_accounts_do_carry_forward(self):
        """The receivable created in March must still show in a period that
        starts in June."""
        options = self._options(date_from="2026-06-01")
        result = self.engine.trial_balance(options)
        openings = [
            line["opening"] for line in result["lines"]
            if line["group"] == "asset"
        ]
        self.assertTrue(any(openings), "no asset carried an opening balance")

    # ------------------------------------------------------------------
    # Profit and loss
    # ------------------------------------------------------------------

    def test_profit_and_loss_figures(self):
        result = self.engine.profit_and_loss(self._options())
        self.assertAlmostEqual(result["income_total"], 1000.0, places=2)
        self.assertAlmostEqual(result["expense_total"], 400.0, places=2)
        self.assertAlmostEqual(result["net_result"], 600.0, places=2)

    def test_income_is_shown_positive(self):
        """Odoo stores income as a credit, so the raw balance is negative. A
        statement showing negative revenue would be nonsense."""
        result = self.engine.profit_and_loss(self._options())
        income_sections = [
            s for s in result["sections"]
            if s["account_type"].startswith("income")
        ]
        self.assertTrue(income_sections)
        for section in income_sections:
            self.assertGreater(section["total"], 0.0)

    def test_period_outside_the_entries_is_empty(self):
        result = self.engine.profit_and_loss(
            self._options(date_from="2020-01-01", date_to="2020-12-31")
        )
        self.assertAlmostEqual(result["net_result"], 0.0, places=2)

    # ------------------------------------------------------------------
    # Balance sheet
    # ------------------------------------------------------------------

    def test_balance_sheet_balances(self):
        """Assets must equal liabilities plus equity, with the period's result
        counted as equity because the year has not been closed."""
        result = self.engine.balance_sheet(self._options())
        self.assertTrue(
            result["balanced"],
            "assets %s vs liabilities and equity %s"
            % (result["assets_total"], result["liabilities_and_equity"]),
        )

    def test_balance_sheet_includes_the_current_result(self):
        result = self.engine.balance_sheet(self._options())
        self.assertAlmostEqual(result["current_result"], 600.0, places=2)

    def test_balance_sheet_without_the_result_would_not_balance(self):
        """Guards the reason the current result is added at all."""
        result = self.engine.balance_sheet(self._options())
        equity_without_result = (
            result["equity_total"] - result["current_result"]
        )
        self.assertNotAlmostEqual(
            result["assets_total"],
            result["liabilities_total"] + equity_without_result,
            places=2,
        )

    # ------------------------------------------------------------------
    # Filters
    # ------------------------------------------------------------------

    def test_draft_entries_excluded_by_default(self):
        draft = self.init_invoice(
            "out_invoice", invoice_date="2026-04-01", amounts=[9999.0], taxes=[]
        )
        self.assertEqual(draft.state, "draft")
        result = self.engine.profit_and_loss(self._options())
        self.assertAlmostEqual(result["income_total"], 1000.0, places=2)

    def test_draft_entries_included_when_asked(self):
        draft = self.init_invoice(
            "out_invoice", invoice_date="2026-04-01", amounts=[500.0], taxes=[]
        )
        self.assertEqual(draft.state, "draft")
        result = self.engine.profit_and_loss(self._options(posted_only=False))
        self.assertAlmostEqual(result["income_total"], 1500.0, places=2)

    def test_hide_zero_accounts(self):
        with_zeros = self.engine.trial_balance(self._options(hide_zero=False))
        without = self.engine.trial_balance(self._options(hide_zero=True))
        self.assertGreaterEqual(
            len(with_zeros["lines"]), len(without["lines"])
        )

    def test_dates_the_wrong_way_round_are_refused(self):
        from odoo.exceptions import UserError
        wizard = self._wizard(date_from="2026-12-31", date_to="2026-01-01")
        with self.assertRaises(UserError):
            wizard._options()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def test_every_report_renders(self):
        for report_type in ("trial_balance", "profit_and_loss", "balance_sheet"):
            with self.subTest(report_type):
                wizard = self._wizard(report_type)
                html, _kind = self.env["ir.actions.report"]._render_qweb_html(
                    "hm_account_reports.report_financial", wizard.ids
                )
                content = html.decode() if isinstance(html, bytes) else html
                self.assertIn("Total", content)

    def test_draft_warning_appears_on_the_report(self):
        wizard = self._wizard(posted_only=False)
        html, _kind = self.env["ir.actions.report"]._render_qweb_html(
            "hm_account_reports.report_financial", wizard.ids
        )
        content = html.decode() if isinstance(html, bytes) else html
        self.assertIn("Not suitable for filing", content)
