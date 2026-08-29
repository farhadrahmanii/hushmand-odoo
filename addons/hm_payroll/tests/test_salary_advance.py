# Part of hm_payroll. See LICENSE file for full copyright and licensing details.
"""Tests for salary advances and their recovery.

The properties that matter are arithmetic and exclusivity: a schedule that
adds up to exactly the advance, and an instalment that can be recovered by
one payslip and no other -- including when a payslip is recomputed, deleted
or cancelled.
"""

from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestSalaryAdvance(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        groups = (
            cls.env.ref("hr.group_hr_manager")
            + cls.env.ref("hm_payroll.group_payroll_manager")
        )
        groups.sudo().write({"user_ids": [(4, cls.env.user.id)]})

        cls.employee = cls.env["hr.employee"].create({"name": "Nasrin Ahmadi"})
        cls.employee.version_id.wage = 20000.0

        cls.structure = cls.env["hm.payroll.structure"].create({
            "name": "With Advance Recovery",
            "rule_ids": [
                (0, 0, {
                    "name": "Basic Salary",
                    "code": "BASIC",
                    "sequence": 10,
                    "category_id": cls.env.ref("hm_payroll.category_basic").id,
                    "amount_select": "code",
                    "amount_python": "result = version.wage",
                }),
                (0, 0, {
                    "name": "Gross",
                    "code": "GROSS",
                    "sequence": 30,
                    "category_id": cls.env.ref("hm_payroll.category_gross").id,
                    "amount_select": "code",
                    "amount_python": "result = categories['BASIC']",
                    "appears_on_payslip": False,
                }),
                (0, 0, {
                    "name": "Advance Recovery",
                    "code": "ADV",
                    "sequence": 40,
                    "category_id": cls.env.ref(
                        "hm_payroll.category_deduction").id,
                    "amount_select": "code",
                    "amount_python": "result = -inputs.get('ADVANCE', 0.0)",
                }),
                (0, 0, {
                    "name": "Net",
                    "code": "NET",
                    "sequence": 50,
                    "category_id": cls.env.ref("hm_payroll.category_net").id,
                    "amount_select": "code",
                    "amount_python":
                        "result = categories['GROSS'] + categories['DED']",
                }),
            ],
        })

    def _advance(self, **values):
        data = {
            "employee_id": self.employee.id,
            "date": "2026-01-15",
            "amount": 9000.0,
            "installments": 3,
            "date_first_recovery": "2026-02-01",
        }
        data.update(values)
        return self.env["hm.salary.advance"].create(data)

    def _slip(self, date_from, date_to):
        return self.env["hm.payslip"].create({
            "employee_id": self.employee.id,
            "structure_id": self.structure.id,
            "date_from": date_from,
            "date_to": date_to,
        })

    # ------------------------------------------------------------------
    # The schedule adds up
    # ------------------------------------------------------------------

    def test_schedule_totals_the_advance(self):
        """The property that matters most: recover exactly what was lent,
        no more and no less."""
        advance = self._advance()
        advance.action_approve()
        self.assertEqual(len(advance.line_ids), 3)
        self.assertAlmostEqual(
            sum(advance.line_ids.mapped("amount")), 9000.0, places=2
        )

    def test_an_indivisible_advance_still_totals_exactly(self):
        """10,000 over 3 is 3,333.33 twice and 3,333.34 once. Dividing alone
        would leave a cent unrecovered for ever."""
        advance = self._advance(amount=10000.0, installments=3)
        advance.action_approve()
        self.assertAlmostEqual(
            sum(advance.line_ids.mapped("amount")), 10000.0, places=2
        )

    def test_instalments_fall_in_consecutive_months(self):
        advance = self._advance()
        advance.action_approve()
        dates = advance.line_ids.sorted("sequence").mapped("date")
        self.assertEqual(
            [str(d) for d in dates],
            ["2026-02-01", "2026-03-01", "2026-04-01"],
        )

    def test_recovery_defaults_to_the_month_after_the_advance(self):
        advance = self._advance(date_first_recovery=False)
        advance.action_approve()
        self.assertEqual(str(advance.line_ids[0].date), "2026-02-15")

    def test_a_single_instalment_takes_the_whole_advance(self):
        advance = self._advance(installments=1)
        advance.action_approve()
        self.assertEqual(len(advance.line_ids), 1)
        self.assertAlmostEqual(advance.line_ids.amount, 9000.0, places=2)

    # ------------------------------------------------------------------
    # Recovery through payslips
    # ------------------------------------------------------------------

    def test_a_payslip_deducts_the_instalment_due(self):
        advance = self._advance()
        advance.action_approve()

        slip = self._slip("2026-02-01", "2026-02-28")
        slip.action_compute_sheet()

        self.assertAlmostEqual(slip.advance_due, 3000.0, places=2)
        line = slip.line_ids.filtered(lambda l: l.code == "ADV")
        self.assertAlmostEqual(line.total, -3000.0, places=2)
        self.assertAlmostEqual(slip.net_wage, 17000.0, places=2)

    def test_nothing_is_deducted_before_the_first_instalment_is_due(self):
        advance = self._advance()
        advance.action_approve()
        slip = self._slip("2026-01-01", "2026-01-31")
        slip.action_compute_sheet()
        self.assertAlmostEqual(slip.advance_due, 0.0, places=2)
        self.assertAlmostEqual(slip.net_wage, 20000.0, places=2)

    def test_recovery_is_recorded_only_once_the_payslip_is_confirmed(self):
        """Computing a payslip claims the instalment so nothing else can take
        it, but the money has not actually been withheld until the payslip is
        confirmed."""
        advance = self._advance()
        advance.action_approve()

        slip = self._slip("2026-02-01", "2026-02-28")
        slip.action_compute_sheet()
        self.assertAlmostEqual(advance.amount_recovered, 0.0, places=2)
        self.assertAlmostEqual(advance.amount_outstanding, 9000.0, places=2)

        slip.action_confirm()
        self.assertAlmostEqual(advance.amount_recovered, 3000.0, places=2)
        self.assertAlmostEqual(advance.amount_outstanding, 6000.0, places=2)

    def test_two_payslips_cannot_recover_the_same_instalment(self):
        """The whole point of claiming at compute time."""
        advance = self._advance()
        advance.action_approve()

        first = self._slip("2026-02-01", "2026-02-28")
        first.action_compute_sheet()
        second = self._slip("2026-02-01", "2026-02-28")
        second.action_compute_sheet()

        self.assertAlmostEqual(first.advance_due, 3000.0, places=2)
        self.assertAlmostEqual(second.advance_due, 0.0, places=2)

    def test_a_later_payslip_sweeps_up_an_instalment_that_was_missed(self):
        """Instalments are due by a date, not on it, so skipping a month does
        not lose the money."""
        advance = self._advance()
        advance.action_approve()
        slip = self._slip("2026-04-01", "2026-04-30")
        slip.action_compute_sheet()
        self.assertAlmostEqual(slip.advance_due, 9000.0, places=2)

    def test_recovering_every_instalment_closes_the_advance(self):
        advance = self._advance(installments=1)
        advance.action_approve()
        slip = self._slip("2026-02-01", "2026-02-28")
        slip.action_compute_sheet()
        slip.action_confirm()
        self.assertEqual(advance.state, "done")
        self.assertAlmostEqual(advance.amount_outstanding, 0.0, places=2)

    # ------------------------------------------------------------------
    # Putting instalments back
    # ------------------------------------------------------------------

    def test_cancelling_a_payslip_makes_the_advance_owed_again(self):
        advance = self._advance(installments=1)
        advance.action_approve()
        slip = self._slip("2026-02-01", "2026-02-28")
        slip.action_compute_sheet()
        slip.action_confirm()
        self.assertEqual(advance.state, "done")

        slip.action_cancel()
        self.assertAlmostEqual(advance.amount_recovered, 0.0, places=2)
        self.assertAlmostEqual(advance.amount_outstanding, 9000.0, places=2)
        self.assertEqual(advance.state, "approved")

        later = self._slip("2026-03-01", "2026-03-31")
        later.action_compute_sheet()
        self.assertAlmostEqual(later.advance_due, 9000.0, places=2)

    def test_deleting_a_draft_payslip_releases_its_claim(self):
        advance = self._advance()
        advance.action_approve()
        slip = self._slip("2026-02-01", "2026-02-28")
        slip.action_compute_sheet()
        slip.unlink()

        other = self._slip("2026-02-01", "2026-02-28")
        other.action_compute_sheet()
        self.assertAlmostEqual(other.advance_due, 3000.0, places=2)

    def test_recomputing_for_an_earlier_period_gives_the_instalment_back(self):
        advance = self._advance()
        advance.action_approve()
        slip = self._slip("2026-02-01", "2026-02-28")
        slip.action_compute_sheet()
        self.assertAlmostEqual(slip.advance_due, 3000.0, places=2)

        slip.write({"date_from": "2026-01-01", "date_to": "2026-01-31"})
        slip.action_compute_sheet()
        self.assertAlmostEqual(slip.advance_due, 0.0, places=2)
        self.assertAlmostEqual(advance.amount_outstanding, 9000.0, places=2)

    # ------------------------------------------------------------------
    # Guards
    # ------------------------------------------------------------------

    def test_an_advance_already_recovered_cannot_be_cancelled(self):
        advance = self._advance()
        advance.action_approve()
        slip = self._slip("2026-02-01", "2026-02-28")
        slip.action_compute_sheet()
        slip.action_confirm()
        with self.assertRaises(UserError):
            advance.action_cancel()

    def test_an_approved_advance_cannot_be_deleted(self):
        advance = self._advance()
        advance.action_approve()
        with self.assertRaises(UserError):
            advance.unlink()

    def test_a_recovered_instalment_cannot_be_deleted(self):
        advance = self._advance()
        advance.action_approve()
        slip = self._slip("2026-02-01", "2026-02-28")
        slip.action_compute_sheet()
        slip.action_confirm()
        recovered = advance.line_ids.filtered("recovered")
        with self.assertRaises(UserError):
            recovered.unlink()

    def test_only_a_draft_advance_can_be_approved(self):
        advance = self._advance()
        advance.action_approve()
        with self.assertRaises(UserError):
            advance.action_approve()

    def test_a_manual_input_overrides_the_automatic_recovery(self):
        """An officer who types an ADVANCE input has decided to recover a
        different amount this month; the automatic figure must not silently
        replace their number."""
        advance = self._advance()
        advance.action_approve()
        slip = self._slip("2026-02-01", "2026-02-28")
        slip.write({"input_line_ids": [(0, 0, {
            "name": "Reduced recovery",
            "code": "ADVANCE",
            "amount": 500.0,
        })]})
        slip.action_compute_sheet()
        line = slip.line_ids.filtered(lambda l: l.code == "ADV")
        self.assertAlmostEqual(line.total, -500.0, places=2)


@tagged("post_install", "-at_install")
class TestPayslipReport(AccountTestInvoicingCommon):
    """The printed payslip is what the employee is actually handed."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        groups = (
            cls.env.ref("hr.group_hr_manager")
            + cls.env.ref("hm_payroll.group_payroll_manager")
        )
        groups.sudo().write({"user_ids": [(4, cls.env.user.id)]})

        cls.employee = cls.env["hr.employee"].create({"name": "Karim Zadran"})
        cls.employee.version_id.wage = 15000.0
        cls.structure = cls.env["hm.payroll.structure"].create({
            "name": "Simple",
            "rule_ids": [
                (0, 0, {
                    "name": "Basic Salary",
                    "code": "BASIC",
                    "sequence": 10,
                    "category_id": cls.env.ref("hm_payroll.category_basic").id,
                    "amount_select": "code",
                    "amount_python": "result = version.wage",
                }),
                (0, 0, {
                    "name": "Hidden Working Total",
                    "code": "HIDDEN",
                    "sequence": 20,
                    "category_id": cls.env.ref("hm_payroll.category_gross").id,
                    "amount_select": "code",
                    "amount_python": "result = categories['BASIC']",
                    "appears_on_payslip": False,
                }),
                (0, 0, {
                    "name": "Net",
                    "code": "NET",
                    "sequence": 50,
                    "category_id": cls.env.ref("hm_payroll.category_net").id,
                    "amount_select": "code",
                    "amount_python": "result = categories['GROSS']",
                }),
            ],
        })

    def _rendered(self):
        slip = self.env["hm.payslip"].create({
            "employee_id": self.employee.id,
            "structure_id": self.structure.id,
            "date_from": "2026-03-01",
            "date_to": "2026-03-31",
        })
        slip.action_compute_sheet()
        html, _dummy = self.env["ir.actions.report"]._render_qweb_html(
            "hm_payroll.report_hm_payslip", slip.ids
        )
        return slip, html.decode() if isinstance(html, bytes) else html

    def test_the_payslip_renders(self):
        slip, html = self._rendered()
        self.assertIn("Karim Zadran", html)
        self.assertIn("Basic Salary", html)

    def test_lines_hidden_from_the_payslip_are_not_printed(self):
        """appears_on_payslip exists for this. A working total the employee
        should not see must not appear on the document they are handed."""
        slip, html = self._rendered()
        self.assertIn("Basic Salary", html)
        self.assertNotIn("Hidden Working Total", html)

    def test_the_net_is_printed_in_words(self):
        slip, html = self._rendered()
        self.assertIn("In words", html)
