# Part of af_hr_payroll. See LICENSE file for full copyright and licensing details.
"""Tests for Afghan wage withholding.

Tax arithmetic is worth testing at the boundaries rather than in the middle of
a band. Almost any wrong implementation still gets 50,000 right; what it gets
wrong is the afghani either side of 12,500.
"""

from psycopg2 import IntegrityError

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TaxCase(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        groups = (
            cls.env.ref("hr.group_hr_manager")
            + cls.env.ref("hm_payroll.group_payroll_manager")
        )
        groups.sudo().write({"user_ids": [(4, cls.env.user.id)]})
        cls.company = cls.env.company
        cls.afn = cls.env.ref("base.AFN")
        cls.scale = cls.env.ref("af_hr_payroll.tax_scale_af")
        cls.scale.company_id = cls.company

    def _scale(self, brackets, **kwargs):
        """Build a scale from (from, to, base, rate) tuples."""
        vals = {
            "name": "Test scale",
            "date_from": "2020-01-01",
            "currency_id": self.afn.id,
            "bracket_ids": [
                (0, 0, {"amount_from": f, "amount_to": t,
                        "base_amount": b, "rate": r})
                for f, t, b, r in brackets
            ],
        }
        vals.update(kwargs)
        return self.env["af.income.tax.scale"].create(vals)


class TestTheBrackets(TaxCase):
    """The supplied Afghan scale, read at every edge."""

    def _tax(self, amount):
        return self.scale.compute_tax(amount)

    def test_below_the_threshold_is_untaxed(self):
        self.assertEqual(self._tax(4000), 0.0)

    def test_exactly_at_the_threshold_is_untaxed(self):
        """5,000 is the top of the zero band, not the bottom of the next."""
        self.assertEqual(self._tax(5000), 0.0)

    def test_one_afghani_over_the_threshold_pays_two_percent_of_one(self):
        """Not 2% of 5,001. The rate applies to the part inside the bracket,
        which is the whole point of a progressive scale."""
        self.assertAlmostEqual(self._tax(5001), 0.02, places=2)

    def test_middle_of_the_two_percent_band(self):
        self.assertAlmostEqual(self._tax(10000), 100.0, places=2)

    def test_top_of_the_two_percent_band(self):
        self.assertAlmostEqual(self._tax(12500), 150.0, places=2)

    def test_just_into_the_ten_percent_band(self):
        self.assertAlmostEqual(self._tax(12501), 150.10, places=2)

    def test_middle_of_the_ten_percent_band(self):
        self.assertAlmostEqual(self._tax(50000), 3900.0, places=2)

    def test_top_of_the_ten_percent_band(self):
        self.assertAlmostEqual(self._tax(100000), 8900.0, places=2)

    def test_just_into_the_twenty_percent_band(self):
        self.assertAlmostEqual(self._tax(100001), 8900.20, places=2)

    def test_well_into_the_top_band(self):
        self.assertAlmostEqual(self._tax(200000), 28900.0, places=2)

    def test_zero_and_negative_pay_nothing(self):
        self.assertEqual(self._tax(0), 0.0)
        self.assertEqual(self._tax(-5000), 0.0)

    def test_the_scale_is_continuous_at_every_boundary(self):
        """The real property a progressive scale has to have: earning one
        more afghani never costs more than one afghani in tax. A wrong
        base_amount passes every single-point test above and fails this."""
        for boundary in (5000, 12500, 100000):
            below = self._tax(boundary)
            above = self._tax(boundary + 1)
            self.assertLess(
                above - below, 1.0,
                "crossing %s costs %.2f in tax for 1 more afghani of salary"
                % (boundary, above - below),
            )

    def test_tax_never_exceeds_the_salary(self):
        for salary in (5001, 12501, 100001, 1000000):
            self.assertLess(self._tax(salary), salary)


class TestTheScaleIsAScale(TaxCase):
    """A gap or an overlap is invisible on screen and wrong on a payslip."""

    def test_a_gap_between_brackets_is_refused(self):
        with self.assertRaises(ValidationError):
            self._scale([(0, 5000, 0, 0), (6000, 0, 0, 10)])

    def test_an_overlap_is_refused(self):
        with self.assertRaises(ValidationError):
            self._scale([(0, 5000, 0, 0), (4000, 0, 0, 10)])

    def test_not_starting_at_zero_is_refused(self):
        with self.assertRaises(ValidationError):
            self._scale([(1000, 5000, 0, 0), (5000, 0, 0, 10)])

    def test_a_closed_top_bracket_is_refused(self):
        """A ceiling on the highest bracket means a big enough salary falls
        off the top of the scale and is taxed nothing at all."""
        with self.assertRaises(ValidationError):
            self._scale([(0, 5000, 0, 0), (5000, 100000, 0, 10)])

    def test_a_middle_bracket_left_open_is_refused(self):
        with self.assertRaises(ValidationError):
            self._scale([(0, 0, 0, 0), (5000, 0, 0, 10)])

    # The database raises these, and Odoo logs them at ERROR. CI greps the
    # log for ERROR, so an expected violation has to be muted or a passing
    # test fails the build.
    @mute_logger("odoo.sql_db")
    def test_a_rate_over_one_hundred_percent_is_refused(self):
        with self.assertRaises(IntegrityError):
            self._scale([(0, 0, 0, 150)])
            self.env.flush_all()

    @mute_logger("odoo.sql_db")
    def test_a_bracket_ending_below_its_start_is_refused(self):
        with self.assertRaises(IntegrityError):
            self._scale([(0, 0, 0, 0), (5000, 1000, 0, 10)])
            self.env.flush_all()

    def test_a_single_open_bracket_is_a_valid_flat_tax(self):
        flat = self._scale([(0, 0, 0, 10)])
        self.assertAlmostEqual(flat.compute_tax(1000), 100.0, places=2)


class TestWhichScaleApplies(TaxCase):

    def test_the_scale_in_force_on_the_date_is_chosen(self):
        old = self._scale([(0, 0, 0, 10)],
                          date_from="2020-01-01", date_to="2020-12-31")
        new = self._scale([(0, 0, 0, 20)], date_from="2021-01-01")
        Scale = self.env["af.income.tax.scale"]
        self.assertEqual(Scale._scale_for("2020-06-01"), old)
        self.assertEqual(Scale._scale_for("2021-06-01"), new)

    def test_no_scale_before_the_earliest_start(self):
        self.env["af.income.tax.scale"].search([]).unlink()
        self._scale([(0, 0, 0, 10)], date_from="2021-01-01")
        self.assertFalse(
            self.env["af.income.tax.scale"]._scale_for("2019-01-01")
        )


class TestPeriodLength(TaxCase):
    """The scale is monthly. Anything else has to be annualised first."""

    def _slip(self, date_from, date_to):
        employee = self.env["hr.employee"].create({"name": "Test Person"})
        return self.env["hm.payslip"].new({
            "employee_id": employee.id,
            "date_from": date_from,
            "date_to": date_to,
            "company_id": self.company.id,
        })

    def test_a_calendar_month_is_twelve(self):
        self.assertEqual(
            self._slip("2026-01-01", "2026-01-31")._af_periods_per_year(), 12.0
        )

    def test_february_is_still_twelve(self):
        """A 28-day month and a 31-day month are both a month. Dividing by an
        exact day count would tax February differently from January."""
        self.assertEqual(
            self._slip("2026-02-01", "2026-02-28")._af_periods_per_year(), 12.0
        )

    def test_a_fortnight_is_twenty_six(self):
        self.assertEqual(
            self._slip("2026-01-01", "2026-01-14")._af_periods_per_year(), 26.0
        )

    def test_a_fortnight_is_taxed_as_half_a_month_not_as_a_poor_month(self):
        """5,000 a fortnight is 10,833 a month, which is taxable. Read
        against the monthly brackets directly it would look like it sits in
        the zero band and pay nothing."""
        annualised = self.scale.compute_tax(5000, periods_per_year=26.0)
        self.assertGreater(annualised, 0.0)
        self.assertAlmostEqual(annualised, 53.85, places=2)

    def test_the_same_annual_wage_pays_the_same_tax_either_way(self):
        """The real invariant: how often somebody is paid must not change
        what they owe for the year."""
        monthly = self.scale.compute_tax(26000, periods_per_year=12.0) * 12
        fortnightly = self.scale.compute_tax(12000, periods_per_year=26.0) * 26
        self.assertAlmostEqual(monthly, fortnightly, places=2)


class TestTheWholeChain(TaxCase):
    """A real payslip through the shipped structure.

    This is the test that proves the rule engine can actually call the
    function the module injects. Everything above tests arithmetic in
    isolation; a typo in the rule's Python, or a safe_eval that refuses to
    call a bound method, only shows up here.

    It is also the Kabul case rather than a simplified one: the company keeps
    its books in dollars, staff are paid in dollars, and the tax is assessed
    in afghani. Everything is converted at the month's agreed rate of 70.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.structure = cls.env.ref("af_hr_payroll.structure_af_monthly")
        # The structure is loaded from XML and lands on whichever company is
        # the main one; this test suite runs under its own. hm_payroll refuses
        # a payslip whose structure belongs elsewhere, which is the right
        # refusal -- it just has to be satisfied here.
        cls.structure.company_id = cls.company

        cls.afn.active = True
        cls.company.af_secondary_currency_id = cls.afn
        cls.period = cls.env["af.exchange.period"].create({
            "name": "2026-01",
            "company_id": cls.company.id,
            "currency_id": cls.afn.id,
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
            "rate": 70.0,
        })
        cls.period.action_confirm()

        cls.employee = cls.env["hr.employee"].create({"name": "Zahra Nabizada"})
        cls.employee.version_id.wage = 1000.0

    def _payslip(self, **vals):
        slip = self.env["hm.payslip"].create(dict({
            "employee_id": self.employee.id,
            "structure_id": self.structure.id,
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        }, **vals))
        slip.action_compute_sheet()
        return slip

    def _line(self, slip, code):
        return slip.line_ids.filtered(lambda l: l.code == code)

    def test_a_payslip_computes_the_tax_line(self):
        slip = self._payslip()
        tax = self._line(slip, "TAX")
        self.assertTrue(tax, "the structure produced no TAX line")
        # $1,000 gross is 70,000 AFN. Tax there is 150 + 10% of the 57,500
        # above 12,500, so 5,900 AFN, which is $84.29 back at the same rate.
        self.assertAlmostEqual(tax.total, -84.29, places=2)

    def test_the_tax_is_assessed_in_afghani_not_on_the_dollar_figure(self):
        """The distinction the module exists for. Read against the brackets
        as though $1,000 were 1,000 afghani, the tax would be 100 afghani --
        under a hundredth of what is actually owed."""
        self.assertAlmostEqual(self._line(self._payslip(), "TAX").total,
                               -84.29, places=2)
        self.assertNotAlmostEqual(self._line(self._payslip(), "TAX").total,
                                  -100.0, places=2)

    def test_without_a_confirmed_rate_it_refuses_rather_than_guessing(self):
        """A payslip is a legal document. Silently taxing at zero, or at last
        month's rate, is worse than declining to compute."""
        self.period.action_reset_draft()
        with self.assertRaises(UserError) as caught:
            self._payslip()
        self.assertIn("exchange period", str(caught.exception).lower())

    def test_the_tax_line_is_a_deduction(self):
        """Net is gross plus deductions, so the tax has to be negative. A
        positive one would pay the employee their tax instead of withholding
        it, and the payslip would still add up."""
        self.assertLess(self._line(self._payslip(), "TAX").total, 0)

    def test_net_is_gross_less_the_tax(self):
        slip = self._payslip()
        gross = self._line(slip, "GROSS").total
        tax = self._line(slip, "TAX").total
        self.assertAlmostEqual(self._line(slip, "NET").total, gross + tax,
                               places=2)

    def test_an_allowance_input_is_taxed_with_the_salary(self):
        """An allowance is part of gross, so adding one has to move the tax."""
        plain = self._payslip()
        with_allowance = self._payslip(input_line_ids=[
            (0, 0, {"name": "Transport", "code": "ALW", "amount": 4000.0}),
        ])
        self.assertAlmostEqual(
            self._line(with_allowance, "GROSS").total,
            self._line(plain, "GROSS").total + 4000.0, places=2,
        )
        self.assertLess(self._line(with_allowance, "TAX").total,
                        self._line(plain, "TAX").total)

    def test_a_salary_under_the_threshold_is_taxed_nothing(self):
        """$50 is 3,500 AFN, below the 5,000 exemption."""
        self.employee.version_id.wage = 50.0
        self.assertAlmostEqual(self._line(self._payslip(), "TAX").total, 0.0,
                               places=2)

    def test_with_no_scale_in_force_it_refuses_rather_than_taxing_nothing(self):
        """The dangerous failure. Returning zero would produce a payslip that
        looks finished and withholds nothing."""
        self.env["af.income.tax.scale"].search([]).unlink()
        with self.assertRaises(UserError) as caught:
            self._payslip()
        self.assertIn("tax scale", str(caught.exception).lower())
