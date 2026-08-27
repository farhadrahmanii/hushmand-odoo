# Part of hm_contracts. See LICENSE file for full copyright and licensing details.
"""Tests for service contracts.

The behaviour worth guarding is that billing advances correctly and that
nothing is invoiced without a person asking for it.
"""

from datetime import timedelta

from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class ContractCase(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.context_today(cls.env["hm.contract"])
        cls.customer = cls.env["res.partner"].create({"name": "Test Customer"})
        cls.Contract = cls.env["hm.contract"]

    def _contract(self, lines=True, **values):
        data = {
            "title": "Annual security services",
            "partner_id": self.customer.id,
            "date_start": self.today,
            "recurrence": "1",
        }
        data.update(values)
        if lines:
            data["line_ids"] = [(0, 0, {
                "name": "Guarding, 2 posts",
                "quantity": 2,
                "price_unit": 500.0,
            })]
        return self.Contract.create(data)


class TestAmounts(ContractCase):

    def test_reference_generated(self):
        self.assertIn("SC/", self._contract().name)

    def test_per_period_total(self):
        self.assertAlmostEqual(
            self._contract().amount_recurring, 1000.0, places=2
        )

    def test_annualised_monthly(self):
        contract = self._contract(recurrence="1")
        self.assertAlmostEqual(contract.amount_annual, 12000.0, places=2)

    def test_annualised_quarterly(self):
        """Contracts on different cycles have to be comparable."""
        contract = self._contract(recurrence="3")
        self.assertAlmostEqual(contract.amount_annual, 4000.0, places=2)

    def test_annualised_yearly(self):
        contract = self._contract(recurrence="12")
        self.assertAlmostEqual(contract.amount_annual, 1000.0, places=2)


class TestLifecycle(ContractCase):

    def test_cannot_start_without_lines(self):
        with self.assertRaises(UserError):
            self._contract(lines=False).action_start()

    def test_starting_sets_the_first_invoice_date(self):
        contract = self._contract()
        contract.action_start()
        self.assertEqual(contract.state, "running")
        self.assertEqual(contract.date_next_invoice, contract.date_start)

    def test_open_ended_contract_stays_running(self):
        contract = self._contract(date_end=False)
        contract.action_start()
        contract._refresh_state()
        self.assertEqual(contract.state, "running")

    def test_becomes_expiring_inside_the_notice_period(self):
        contract = self._contract(
            date_end=self.today + timedelta(days=10), notice_days=30,
        )
        contract.action_start()
        contract._refresh_state()
        self.assertEqual(contract.state, "expiring")

    def test_state_refreshes_when_the_term_changes(self):
        """Waiting for tomorrow's job would be wrong on screen now."""
        contract = self._contract(
            date_end=self.today + timedelta(days=365), notice_days=30,
        )
        contract.action_start()
        self.assertEqual(contract.state, "running")

        contract.date_end = self.today + timedelta(days=5)
        self.assertEqual(contract.state, "expiring")

    def test_closes_once_the_end_date_passes(self):
        contract = self._contract(date_end=self.today + timedelta(days=1))
        contract.action_start()
        contract.date_end = self.today - timedelta(days=1)
        self.assertEqual(contract.state, "closed")

    def test_renew_extends_by_one_term(self):
        end = self.today + timedelta(days=10)
        contract = self._contract(date_end=end, recurrence="12")
        contract.action_start()
        contract.action_renew()
        self.assertGreater(contract.date_end, end)
        self.assertEqual(contract.state, "running")

    def test_cannot_renew_an_open_ended_contract(self):
        contract = self._contract(date_end=False)
        contract.action_start()
        with self.assertRaises(UserError):
            contract.action_renew()


class TestInvoicing(ContractCase):

    def test_creating_an_invoice_leaves_it_in_draft(self):
        """A draft raised by a machine that nobody reads is how a customer
        gets billed for a service that stopped months ago."""
        contract = self._contract()
        contract.action_start()
        contract.action_create_invoice()

        invoice = contract.invoice_ids
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.state, "draft")

    def test_invoice_carries_the_lines(self):
        contract = self._contract()
        contract.action_start()
        contract.action_create_invoice()

        line = contract.invoice_ids.invoice_line_ids
        self.assertEqual(len(line), 1)
        self.assertAlmostEqual(line.quantity, 2.0, places=2)
        self.assertAlmostEqual(line.price_unit, 500.0, places=2)

    def test_invoice_links_back_to_the_contract(self):
        contract = self._contract()
        contract.action_start()
        contract.action_create_invoice()
        self.assertEqual(contract.invoice_ids.hm_contract_id, contract)
        self.assertEqual(contract.invoice_count, 1)

    def test_next_invoice_date_advances_by_the_cycle(self):
        contract = self._contract(recurrence="3")
        contract.action_start()
        first_due = contract.date_next_invoice
        contract.action_create_invoice()

        self.assertGreater(contract.date_next_invoice, first_due)
        gap = (contract.date_next_invoice - first_due).days
        self.assertGreaterEqual(gap, 89)
        self.assertLessEqual(gap, 93)

    def test_cannot_invoice_a_draft_contract(self):
        with self.assertRaises(UserError):
            self._contract().action_create_invoice()

    def test_supplier_contracts_do_not_raise_invoices(self):
        """We do not invoice ourselves on somebody else's behalf."""
        contract = self._contract(contract_type="supplier")
        contract.action_start()
        with self.assertRaises(UserError):
            contract.action_create_invoice()

    def test_cancel_is_refused_once_invoiced(self):
        contract = self._contract()
        contract.action_start()
        contract.action_create_invoice()
        with self.assertRaises(UserError):
            contract.action_cancel()


class TestTheDailyJob(ContractCase):

    def _activities(self, contract):
        return self.env["mail.activity"].search([
            ("res_model", "=", "hm.contract"),
            ("res_id", "=", contract.id),
        ])

    def test_nothing_is_invoiced_automatically(self):
        """The job asks a person; it does not bill on their behalf."""
        contract = self._contract()
        contract.action_start()
        contract.date_next_invoice = self.today

        self.Contract._cron_contracts()

        self.assertFalse(
            contract.invoice_ids,
            "the daily job must not raise invoices by itself",
        )

    def test_due_contracts_raise_an_activity(self):
        contract = self._contract()
        contract.action_start()
        contract.date_next_invoice = self.today

        self.Contract._cron_contracts()
        self.assertTrue(self._activities(contract))

    def test_expiring_contracts_ask_for_a_decision(self):
        contract = self._contract(
            date_end=self.today + timedelta(days=5), notice_days=30,
        )
        contract.action_start()

        self.Contract._cron_contracts()

        self.assertEqual(contract.state, "expiring")
        self.assertTrue(contract.reminder_sent)

    def test_auto_renew_extends_instead_of_asking(self):
        end = self.today + timedelta(days=5)
        contract = self._contract(
            date_end=end, notice_days=30, auto_renew=True, recurrence="12",
        )
        contract.action_start()

        self.Contract._cron_contracts()

        self.assertGreater(contract.date_end, end)
        self.assertEqual(contract.state, "running")

    def test_the_reminder_is_raised_once(self):
        contract = self._contract(
            date_end=self.today + timedelta(days=5), notice_days=30,
        )
        contract.action_start()
        self.Contract._cron_contracts()
        self.Contract._cron_contracts()

        renewal_activities = self._activities(contract).filtered(
            lambda a: "ending" in (a.summary or "")
        )
        self.assertEqual(len(renewal_activities), 1)


class TestValidation(ContractCase):

    @mute_logger("odoo.sql_db")
    def test_end_cannot_precede_start(self):
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self._contract(date_end=self.today - timedelta(days=10))

    @mute_logger("odoo.sql_db")
    def test_line_quantity_must_be_positive(self):
        contract = self._contract()
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                contract.line_ids[0].quantity = 0
