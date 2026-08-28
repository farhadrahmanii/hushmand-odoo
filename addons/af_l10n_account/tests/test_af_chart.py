# Part of af_l10n_account. See LICENSE file for full copyright and licensing details.
"""Tests for the Afghan chart of accounts.

A chart is only useful if it actually installs onto a company and leaves Odoo
able to raise an invoice. These check that, and that the tax treatment lands in
the accounts an Afghan accountant would expect to file from.
"""

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestAfghanChart(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_chart_template("af")
    def setUpClass(cls):
        super().setUpClass()

    def _account(self, code):
        return self.env["account.account"].search([
            ("code", "=", code),
            ("company_ids", "in", self.env.company.ids),
        ], limit=1)

    # ------------------------------------------------------------------
    # The chart installs
    # ------------------------------------------------------------------

    def test_the_chart_is_loaded(self):
        accounts = self.env["account.account"].search([
            ("company_ids", "in", self.env.company.ids),
        ])
        self.assertGreater(len(accounts), 50, "the chart did not load")

    def test_the_country_is_afghanistan(self):
        self.assertEqual(
            self.env.company.account_fiscal_country_id,
            self.env.ref("base.af"),
        )

    def test_receivable_and_payable_are_set(self):
        """Odoo cannot raise an invoice without these."""
        self.assertEqual(
            self.company_data["default_account_receivable"].code, "101001"
        )
        self.assertEqual(
            self.company_data["default_account_payable"].code, "200101"
        )

    def test_dual_currency_cash_accounts_exist(self):
        """An Afghan office holds both, and reconciles them separately."""
        self.assertTrue(self._account("100201"), "no AFN cash account")
        self.assertTrue(self._account("100202"), "no USD cash account")
        self.assertTrue(self._account("100301"), "no AFN bank account")
        self.assertTrue(self._account("100302"), "no USD bank account")

    def test_withholding_accounts_are_separate(self):
        """Salaries, rent and contractors are filed separately, so they
        cannot share one payable account."""
        salaries = self._account("200311")
        rent = self._account("200312")
        contractors = self._account("200313")
        self.assertTrue(salaries and rent and contractors)
        self.assertEqual(len({salaries.id, rent.id, contractors.id}), 3)

    def test_depreciation_accounts_pair_with_the_assets(self):
        for asset_code, accumulated_code in (
            ("102002", "102101"),
            ("102003", "102102"),
            ("102006", "102105"),
        ):
            with self.subTest(asset_code):
                self.assertTrue(self._account(asset_code))
                self.assertTrue(self._account(accumulated_code))

    def test_current_year_earnings_is_typed_correctly(self):
        """Odoo needs exactly one unaffected-earnings account, or the balance
        sheet cannot close the year."""
        unaffected = self.env["account.account"].search([
            ("account_type", "=", "equity_unaffected"),
            ("company_ids", "in", self.env.company.ids),
        ])
        self.assertEqual(len(unaffected), 1)

    # ------------------------------------------------------------------
    # Taxes
    # ------------------------------------------------------------------

    def _tax(self, name_fragment, type_tax_use):
        return self.env["account.tax"].search([
            ("name", "ilike", name_fragment),
            ("type_tax_use", "=", type_tax_use),
            ("company_id", "=", self.env.company.id),
        ], limit=1)

    def test_business_receipts_taxes_exist(self):
        for rate in ("2%", "4%", "10%"):
            with self.subTest(rate):
                tax = self._tax("BRT %s" % rate, "sale")
                self.assertTrue(tax, "missing BRT %s" % rate)
                self.assertAlmostEqual(
                    tax.amount, float(rate.rstrip("%")), places=2
                )

    def test_withholding_taxes_are_negative(self):
        """Withholding reduces what the supplier is paid, so the rate is
        negative. A positive one would add tax to the bill instead."""
        for fragment in ("Withholding 2%", "Withholding 7%"):
            with self.subTest(fragment):
                tax = self._tax(fragment, "purchase")
                self.assertTrue(tax, "missing %s" % fragment)
                self.assertLess(tax.amount, 0.0)

    def test_rent_withholding_rates(self):
        for fragment, rate in (("10% on rent", -10.0), ("15% on rent", -15.0)):
            with self.subTest(fragment):
                tax = self._tax(fragment, "purchase")
                self.assertTrue(tax)
                self.assertAlmostEqual(tax.amount, rate, places=2)

    def test_brt_posts_to_the_brt_payable_account(self):
        """It has to land where the return is filed from."""
        tax = self._tax("BRT 2%", "sale")
        tax_lines = tax.invoice_repartition_line_ids.filtered(
            lambda l: l.repartition_type == "tax"
        )
        self.assertTrue(tax_lines.account_id)
        self.assertEqual(tax_lines.account_id.code, "200301")

    def test_contractor_withholding_posts_separately_from_rent(self):
        contractor = self._tax("Withholding 2%", "purchase")
        rent = self._tax("10% on rent", "purchase")

        contractor_account = contractor.invoice_repartition_line_ids.filtered(
            lambda l: l.repartition_type == "tax"
        ).account_id
        rent_account = rent.invoice_repartition_line_ids.filtered(
            lambda l: l.repartition_type == "tax"
        ).account_id

        self.assertEqual(contractor_account.code, "200313")
        self.assertEqual(rent_account.code, "200312")

    # ------------------------------------------------------------------
    # It works end to end
    # ------------------------------------------------------------------

    def test_an_invoice_can_be_posted_on_this_chart(self):
        """The only test that really matters: a company on this chart can
        issue an invoice and have it hit the ledger."""
        invoice = self.init_invoice(
            "out_invoice", invoice_date="2026-06-15", amounts=[1000.0], taxes=[]
        )
        invoice.action_post()
        self.assertEqual(invoice.state, "posted")
        self.assertAlmostEqual(invoice.amount_total, 1000.0, places=2)

    def test_an_invoice_with_brt_computes_the_tax(self):
        tax = self._tax("BRT 4%", "sale")
        invoice = self.init_invoice(
            "out_invoice", invoice_date="2026-06-15", amounts=[1000.0],
            taxes=tax,
        )
        invoice.action_post()
        self.assertAlmostEqual(invoice.amount_untaxed, 1000.0, places=2)
        self.assertAlmostEqual(invoice.amount_tax, 40.0, places=2)
        self.assertAlmostEqual(invoice.amount_total, 1040.0, places=2)

    def test_withholding_reduces_a_bill(self):
        """2% withheld on a 1,000 bill leaves 980 payable to the supplier and
        20 owed to the ministry."""
        tax = self._tax("Withholding 2%", "purchase")
        bill = self.init_invoice(
            "in_invoice", invoice_date="2026-06-15", amounts=[1000.0],
            taxes=tax,
        )
        bill.action_post()
        self.assertAlmostEqual(bill.amount_untaxed, 1000.0, places=2)
        self.assertAlmostEqual(bill.amount_total, 980.0, places=2)
