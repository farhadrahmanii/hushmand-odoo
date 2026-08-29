# Part of hm_payroll. See LICENSE file for full copyright and licensing details.
"""Tests for the payroll engine.

What matters here is arithmetic and refusal: rules that run in order and see
the category totals before them, a journal entry that balances or is not
created at all, and a batch that cannot pay the same employee twice.
"""

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestPayroll(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.journal = cls.env["account.journal"].search(
            [("type", "=", "general"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        cls.account_expense = cls._account("SALEXP", "expense")
        cls.account_net_payable = cls._account("SALPAY", "liability_current")
        cls.account_tax_payable = cls._account("TAXPAY", "liability_current")

        cls.employee = cls.env["hr.employee"].create({"name": "Ahmad Shah"})
        cls.employee.version_id.wage = 20000.0

        cls.cat_basic = cls.env.ref("hm_payroll.category_basic")
        cls.cat_allowance = cls.env.ref("hm_payroll.category_allowance")
        cls.cat_gross = cls.env.ref("hm_payroll.category_gross")
        cls.cat_deduction = cls.env.ref("hm_payroll.category_deduction")
        cls.cat_net = cls.env.ref("hm_payroll.category_net")

        cls.structure = cls.env["hm.payroll.structure"].create({
            "name": "Monthly Salaries",
            "journal_id": cls.journal.id,
            "rule_ids": [
                (0, 0, {
                    "name": "Basic Salary",
                    "code": "BASIC",
                    "sequence": 10,
                    "category_id": cls.cat_basic.id,
                    "amount_select": "code",
                    "amount_python": "result = version.wage",
                    "account_debit_id": cls.account_expense.id,
                }),
                (0, 0, {
                    "name": "Housing Allowance",
                    "code": "HRA",
                    "sequence": 20,
                    "category_id": cls.cat_allowance.id,
                    "amount_select": "fix",
                    "amount_fix": 2000.0,
                    "account_debit_id": cls.account_expense.id,
                }),
                (0, 0, {
                    "name": "Gross",
                    "code": "GROSS",
                    "sequence": 30,
                    "category_id": cls.cat_gross.id,
                    "amount_select": "code",
                    "amount_python":
                        "result = categories['BASIC'] + categories['ALW']",
                    "appears_on_payslip": False,
                }),
                (0, 0, {
                    "name": "Income Tax",
                    "code": "TAX",
                    "sequence": 40,
                    "category_id": cls.cat_deduction.id,
                    "amount_select": "percentage",
                    "amount_percentage": -10.0,
                    "amount_percentage_base": "categories['GROSS']",
                    # A deduction's negative total flips this to the credit
                    # side, which is where the liability belongs.
                    "account_debit_id": cls.account_tax_payable.id,
                }),
                (0, 0, {
                    "name": "Net",
                    "code": "NET",
                    "sequence": 50,
                    "category_id": cls.cat_net.id,
                    "amount_select": "code",
                    "amount_python":
                        "result = categories['GROSS'] + categories['DED']",
                    "account_credit_id": cls.account_net_payable.id,
                }),
            ],
        })

    @classmethod
    def _account(cls, code, account_type):
        return cls.env["account.account"].create({
            "name": code,
            "code": code,
            "account_type": account_type,
        })

    def _slip(self, **values):
        data = {
            "employee_id": self.employee.id,
            "structure_id": self.structure.id,
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        }
        data.update(values)
        return self.env["hm.payslip"].create(data)

    def _line(self, slip, code):
        return slip.line_ids.filtered(lambda l: l.code == code)

    # ------------------------------------------------------------------
    # The sheet adds up
    # ------------------------------------------------------------------

    def test_compute_builds_the_expected_lines(self):
        """Rules run in sequence order and each sees the category totals of
        the rules before it -- the ordering is the arithmetic."""
        slip = self._slip()
        slip.action_compute_sheet()

        self.assertEqual(len(slip.line_ids), 5)
        self.assertAlmostEqual(self._line(slip, "BASIC").total, 20000.0)
        self.assertAlmostEqual(self._line(slip, "HRA").total, 2000.0)
        self.assertAlmostEqual(self._line(slip, "GROSS").total, 22000.0)
        self.assertAlmostEqual(self._line(slip, "TAX").total, -2200.0)
        self.assertAlmostEqual(self._line(slip, "NET").total, 19800.0)

    def test_summary_reads_the_standard_categories(self):
        slip = self._slip()
        slip.action_compute_sheet()
        self.assertAlmostEqual(slip.basic_wage, 20000.0)
        self.assertAlmostEqual(slip.gross_wage, 22000.0)
        self.assertAlmostEqual(slip.net_wage, 19800.0)

    def test_percentage_shows_base_and_rate_on_the_line(self):
        """A percentage line keeps the base as amount and the percentage as
        rate, so the slip shows how the number was reached."""
        slip = self._slip()
        slip.action_compute_sheet()
        tax = self._line(slip, "TAX")
        self.assertAlmostEqual(tax.amount, 22000.0)
        self.assertAlmostEqual(tax.rate, -10.0)

    def test_condition_excludes_a_rule(self):
        self.env["hm.salary.rule"].create({
            "name": "Executive Bonus",
            "code": "EXEC",
            "sequence": 25,
            "structure_id": self.structure.id,
            "category_id": self.cat_allowance.id,
            "condition_select": "python",
            "condition_python": "version.wage > 50000",
            "amount_select": "fix",
            "amount_fix": 5000.0,
        })
        slip = self._slip()
        slip.action_compute_sheet()
        self.assertFalse(self._line(slip, "EXEC"))

    def test_inputs_reach_the_rules(self):
        self.env["hm.salary.rule"].create({
            "name": "Bonus",
            "code": "BONUS",
            "sequence": 25,
            "structure_id": self.structure.id,
            "category_id": self.cat_allowance.id,
            "amount_select": "code",
            "amount_python": "result = inputs.get('BONUS', 0.0)",
            "account_debit_id": self.account_expense.id,
        })
        slip = self._slip(input_line_ids=[
            (0, 0, {"name": "Eid Bonus", "code": "BONUS", "amount": 500.0}),
        ])
        slip.action_compute_sheet()
        self.assertAlmostEqual(self._line(slip, "BONUS").total, 500.0)
        self.assertAlmostEqual(slip.net_wage, 20250.0)  # +500 gross, -50 tax

    def test_result_qty_and_rate_multiply(self):
        self.env["hm.salary.rule"].create({
            "name": "Overtime",
            "code": "OT",
            "sequence": 26,
            "structure_id": self.structure.id,
            "category_id": self.cat_allowance.id,
            "amount_select": "code",
            "amount_python":
                "result = 50.0\nresult_qty = 4",
        })
        slip = self._slip()
        slip.action_compute_sheet()
        self.assertAlmostEqual(self._line(slip, "OT").total, 200.0)

    def test_recompute_only_in_draft(self):
        slip = self._slip()
        slip.action_compute_sheet()
        slip.action_confirm()
        with self.assertRaises(UserError):
            slip.action_compute_sheet()

    # ------------------------------------------------------------------
    # The entry balances or is refused
    # ------------------------------------------------------------------

    def test_confirm_creates_a_balanced_draft_entry(self):
        slip = self._slip()
        slip.action_compute_sheet()
        slip.action_confirm()

        move = slip.move_id
        self.assertTrue(move)
        self.assertEqual(move.state, "draft")
        self.assertAlmostEqual(sum(move.line_ids.mapped("debit")), 22000.0)
        self.assertAlmostEqual(sum(move.line_ids.mapped("credit")), 22000.0)

        expense = move.line_ids.filtered(
            lambda l: l.account_id == self.account_expense
        )
        self.assertAlmostEqual(expense.debit, 22000.0)  # BASIC + HRA merged
        tax = move.line_ids.filtered(
            lambda l: l.account_id == self.account_tax_payable
        )
        self.assertAlmostEqual(tax.credit, 2200.0)
        net = move.line_ids.filtered(
            lambda l: l.account_id == self.account_net_payable
        )
        self.assertAlmostEqual(net.credit, 19800.0)

    def test_confirm_requires_lines(self):
        slip = self._slip()
        with self.assertRaises(UserError):
            slip.action_confirm()

    def test_unbalanced_accounts_are_refused(self):
        """Dropping the net rule's credit account leaves the entry
        unbalanced; the confirmation must fail rather than post a plug."""
        net_rule = self.structure.rule_ids.filtered(
            lambda r: r.code == "NET"
        )
        net_rule.account_credit_id = False
        slip = self._slip()
        slip.action_compute_sheet()
        with self.assertRaises(UserError):
            slip.action_confirm()

    def test_cancel_deletes_a_draft_entry(self):
        slip = self._slip()
        slip.action_compute_sheet()
        slip.action_confirm()
        move = slip.move_id
        slip.action_cancel()
        self.assertEqual(slip.state, "cancelled")
        self.assertFalse(move.exists())

    def test_cancel_refuses_a_posted_entry(self):
        slip = self._slip()
        slip.action_compute_sheet()
        slip.action_confirm()
        slip.move_id.action_post()
        with self.assertRaises(UserError):
            slip.action_cancel()

    def test_confirmed_slip_cannot_be_deleted(self):
        slip = self._slip()
        slip.action_compute_sheet()
        slip.action_confirm()
        with self.assertRaises(UserError):
            slip.unlink()

    @mute_logger("odoo.sql_db")
    def test_period_dates_must_be_ordered(self):
        with self.assertRaises(Exception):
            self._slip(date_from="2026-02-01", date_to="2026-01-31")

    # ------------------------------------------------------------------
    # Batches
    # ------------------------------------------------------------------

    def test_batch_generates_once_per_employee(self):
        other = self.env["hr.employee"].create({"name": "Zarmina"})
        other.version_id.wage = 30000.0

        run = self.env["hm.payslip.run"].create({
            "name": "January 2026",
            "structure_id": self.structure.id,
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        })
        wizard = self.env["hm.payslip.generate"].create({
            "run_id": run.id,
            "employee_ids": [(6, 0, (self.employee | other).ids)],
        })
        wizard.action_generate()

        self.assertEqual(len(run.slip_ids), 2)
        self.assertTrue(all(run.slip_ids.mapped("line_ids")))

        # Running the wizard again cannot pay anyone twice.
        wizard = self.env["hm.payslip.generate"].create({
            "run_id": run.id,
            "employee_ids": [(6, 0, (self.employee | other).ids)],
        })
        wizard.action_generate()
        self.assertEqual(len(run.slip_ids), 2)

    def test_batch_cannot_close_over_draft_slips(self):
        run = self.env["hm.payslip.run"].create({
            "name": "January 2026",
            "structure_id": self.structure.id,
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        })
        self._slip(run_id=run.id)
        with self.assertRaises(UserError):
            run.action_close()

    def test_batch_confirm_all(self):
        run = self.env["hm.payslip.run"].create({
            "name": "January 2026",
            "structure_id": self.structure.id,
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        })
        slip = self._slip(run_id=run.id)
        slip.action_compute_sheet()
        run.action_confirm_all()
        self.assertEqual(slip.state, "done")
        run.action_close()
        self.assertEqual(run.state, "closed")
