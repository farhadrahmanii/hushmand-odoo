# Part of af_dual_currency. See LICENSE file for full copyright and licensing details.
"""The invoice side, kept in its own file.

These build on Odoo's accounting test scaffolding, which sets up a chart of
accounts. Separating them means a problem here still leaves the exchange
period tests reporting cleanly.
"""

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestInvoiceSecondaryTotal(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.afn = cls.env.ref("base.AFN")
        cls.afn.active = True
        cls.company = cls.env.company
        cls.company.af_secondary_currency_id = cls.afn

        cls.period = cls.env["af.exchange.period"].create({
            "name": "2026-08",
            "company_id": cls.company.id,
            "currency_id": cls.afn.id,
            "date_from": "2026-08-01",
            "date_to": "2026-08-31",
            "rate": 70.0,
        })
        cls.period.action_confirm()

    def test_invoice_shows_the_second_currency_total(self):
        invoice = self.init_invoice(
            "out_invoice", invoice_date="2026-08-15", amounts=[1000.0], taxes=[]
        )
        self.assertAlmostEqual(invoice.amount_total, 1000.0, places=2)
        self.assertAlmostEqual(
            invoice.af_amount_total_secondary, 70000.0, places=2
        )

    def test_invoice_records_which_period_was_used(self):
        """Any figure has to be traceable back to an agreed rate."""
        invoice = self.init_invoice(
            "out_invoice", invoice_date="2026-08-15", amounts=[1000.0], taxes=[]
        )
        self.assertEqual(invoice.af_exchange_period_id, self.period)

    def test_invoice_outside_any_period_shows_zero(self):
        """Zero is deliberate: a missing rate should be obvious, not filled in
        with Odoo's daily rate that nobody agreed to."""
        invoice = self.init_invoice(
            "out_invoice", invoice_date="2030-01-15", amounts=[1000.0], taxes=[]
        )
        self.assertEqual(invoice.af_amount_total_secondary, 0.0)
        self.assertFalse(invoice.af_exchange_period_id)

    def test_total_recomputes_when_the_invoice_changes(self):
        invoice = self.init_invoice(
            "out_invoice", invoice_date="2026-08-15", amounts=[1000.0], taxes=[]
        )
        invoice.invoice_line_ids[0].price_unit = 2000.0
        invoice._compute_af_secondary_amount()
        self.assertAlmostEqual(
            invoice.af_amount_total_secondary, 140000.0, places=2
        )

    def test_no_second_currency_configured(self):
        self.company.af_secondary_currency_id = False
        invoice = self.init_invoice(
            "out_invoice", invoice_date="2026-08-15", amounts=[1000.0], taxes=[]
        )
        self.assertEqual(invoice.af_amount_total_secondary, 0.0)
