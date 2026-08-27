# Part of af_zakat. See LICENSE file for full copyright and licensing details.
"""Tests for zakat administration.

The rules worth enforcing are the ones an administrator would be asked about:
that nothing is distributed which was never collected, and that a fund cannot
be quietly closed while it still holds money owed to beneficiaries.
"""

from odoo.exceptions import UserError, ValidationError
from odoo.tests import common, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class ZakatCase(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fund = cls.env["af.zakat.fund"].create({
            "name": "Ramadan 1447",
            "date_from": "2026-02-01",
            "date_to": "2026-03-31",
        })
        cls.beneficiary = cls.env["af.zakat.beneficiary"].create({
            "name": "Zarmina",
            "father_name": "Karim",
            "category": "faqir",
            "household_size": 6,
        })

    def _contribute(self, amount=1000.0, state="received", **values):
        data = {
            "fund_id": self.fund.id,
            "amount": amount,
            "state": state,
        }
        data.update(values)
        return self.env["af.zakat.contribution"].create(data)

    def _distribute(self, amount=100.0, **values):
        data = {
            "fund_id": self.fund.id,
            "beneficiary_id": self.beneficiary.id,
            "amount": amount,
        }
        data.update(values)
        return self.env["af.zakat.distribution"].create(data)


class TestFundArithmetic(ZakatCase):

    def test_collected_counts_only_received(self):
        """A pledge is not money and must not be distributable."""
        self._contribute(1000.0, state="received")
        self._contribute(5000.0, state="pledged")
        self.assertAlmostEqual(self.fund.amount_collected, 1000.0, places=2)

    def test_distributed_counts_only_paid(self):
        self._contribute(1000.0)
        self._distribute(100.0)
        self.assertAlmostEqual(self.fund.amount_distributed, 0.0, places=2)

        self.fund.distribution_ids.action_mark_paid()
        self.assertAlmostEqual(self.fund.amount_distributed, 100.0, places=2)

    def test_remaining_is_what_is_still_owed(self):
        self._contribute(1000.0)
        self._distribute(300.0).action_mark_paid()
        self.assertAlmostEqual(self.fund.amount_remaining, 700.0, places=2)

    def test_people_helped_counts_each_person_once(self):
        self._contribute(1000.0)
        self._distribute(100.0).action_mark_paid()
        self._distribute(100.0).action_mark_paid()
        self.assertEqual(self.fund.beneficiary_count, 1)

    def test_cancelled_contribution_does_not_count(self):
        contribution = self._contribute(1000.0)
        contribution.action_cancel()
        self.assertAlmostEqual(self.fund.amount_collected, 0.0, places=2)


class TestCannotDistributeWhatWasNotCollected(ZakatCase):
    """The rule an administrator would be asked to demonstrate."""

    def test_paying_more_than_the_fund_holds_is_refused(self):
        self._contribute(500.0)
        distribution = self._distribute(600.0)
        with self.assertRaises(UserError):
            distribution.action_mark_paid()

    def test_paying_exactly_the_balance_is_allowed(self):
        self._contribute(500.0)
        self._distribute(500.0).action_mark_paid()
        self.assertAlmostEqual(self.fund.amount_remaining, 0.0, places=2)

    def test_the_limit_falls_as_distributions_are_paid(self):
        self._contribute(1000.0)
        self._distribute(700.0).action_mark_paid()

        too_much = self._distribute(400.0)
        with self.assertRaises(UserError):
            too_much.action_mark_paid()

        within = self._distribute(300.0)
        within.action_mark_paid()
        self.assertEqual(within.state, "paid")

    def test_a_pledge_does_not_raise_the_limit(self):
        self._contribute(100.0, state="received")
        self._contribute(9000.0, state="pledged")
        with self.assertRaises(UserError):
            self._distribute(500.0).action_mark_paid()

    def test_cannot_pay_twice(self):
        self._contribute(1000.0)
        distribution = self._distribute(100.0)
        distribution.action_mark_paid()
        with self.assertRaises(UserError):
            distribution.action_mark_paid()


class TestClosingAFund(ZakatCase):

    def test_cannot_close_while_money_is_undistributed(self):
        """Undistributed zakat is owed to beneficiaries, not held by the
        organisation, so closing over it is refused."""
        self._contribute(1000.0)
        self._distribute(400.0).action_mark_paid()
        with self.assertRaises(UserError):
            self.fund.action_close()

    def test_can_close_once_everything_is_distributed(self):
        self._contribute(1000.0)
        self._distribute(1000.0).action_mark_paid()
        self.fund.action_close()
        self.assertEqual(self.fund.state, "closed")

    def test_closed_fund_refuses_new_distributions(self):
        self.fund.action_close()
        with self.assertRaises(ValidationError):
            self._distribute(100.0)

    def test_reopen(self):
        self.fund.action_close()
        self.fund.action_reopen()
        self.assertEqual(self.fund.state, "open")


class TestBeneficiaries(ZakatCase):

    def test_history_is_visible_across_funds(self):
        """Repeat assistance has to be visible, or the same households get
        reached twice while others are missed."""
        self._contribute(1000.0)
        self._distribute(200.0).action_mark_paid()

        other_fund = self.env["af.zakat.fund"].create({
            "name": "Eid 1447",
            "date_from": "2026-04-01",
            "date_to": "2026-04-30",
        })
        self.env["af.zakat.contribution"].create({
            "fund_id": other_fund.id, "amount": 500.0, "state": "received",
        })
        self.env["af.zakat.distribution"].create({
            "fund_id": other_fund.id,
            "beneficiary_id": self.beneficiary.id,
            "amount": 150.0,
        }).action_mark_paid()

        self.assertAlmostEqual(self.beneficiary.total_received, 350.0, places=2)
        self.assertEqual(self.beneficiary.distribution_count, 2)

    def test_unpaid_distributions_do_not_count_as_received(self):
        self._contribute(1000.0)
        self._distribute(200.0)
        self.assertAlmostEqual(self.beneficiary.total_received, 0.0, places=2)

    def test_display_name_names_the_father(self):
        self.assertEqual(self.beneficiary.display_name, "Zarmina s/o Karim")

    def test_category_is_carried_onto_the_distribution(self):
        self._contribute(1000.0)
        distribution = self._distribute(100.0)
        self.assertEqual(distribution.category, "faqir")

    @mute_logger("odoo.sql_db")
    def test_household_must_have_someone_in_it(self):
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.env["af.zakat.beneficiary"].create({
                    "name": "Nobody", "category": "faqir", "household_size": 0,
                })


class TestReferences(ZakatCase):

    def test_contribution_reference_generated(self):
        self.assertIn("ZC/", self._contribute().name)

    def test_distribution_reference_generated(self):
        self._contribute(1000.0)
        self.assertIn("ZD/", self._distribute().name)

    def test_anonymous_contribution_still_has_a_record(self):
        contribution = self._contribute(anonymous=True)
        self.assertIn("Anonymous", contribution.display_name)
        self.assertTrue(contribution.name)

    @mute_logger("odoo.sql_db")
    def test_amounts_must_be_positive(self):
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self._contribute(amount=0.0)
