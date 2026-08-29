# Part of hm_payroll. See LICENSE file for full copyright and licensing details.
"""Salary structures and the rules inside them.

A structure is an ordered list of rules; a payslip is the result of running
them top to bottom. The ordering is not cosmetic: each rule sees the running
totals of every category computed before it, which is how a Net rule knows
what Gross came to. Sequence numbers are therefore part of the payroll's
correctness, not just its layout.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


class HmSalaryRuleCategory(models.Model):
    _name = "hm.salary.rule.category"
    _description = "Salary Rule Category"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(
        required=True,
        help="How rules refer to this category's running total, e.g. "
             "categories['GROSS']. Keep it short and stable; payslip "
             "summaries key on BASIC, GROSS and NET.",
    )
    sequence = fields.Integer(default=10)
    note = fields.Text(string="Description")

    _code_uniq = models.Constraint(
        "unique(code)",
        "A salary rule category code must be unique.",
    )


class HmPayrollStructure(models.Model):
    _name = "hm.payroll.structure"
    _description = "Salary Structure"
    _order = "name"

    name = fields.Char(required=True)
    code = fields.Char(string="Reference", copy=False)
    active = fields.Boolean(default=True)
    type_id = fields.Many2one(
        comodel_name="hr.payroll.structure.type",
        string="Structure Type",
        help="The structure type from core HR. An employee's contract "
             "version carries a structure type, which is how a payslip "
             "suggests the right structure.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Salary Journal",
        domain="[('type', '=', 'general')]",
        help="Where confirmed payslips create their journal entry. Leave "
             "empty for a structure that is purely informational and never "
             "posts.",
    )
    rule_ids = fields.One2many(
        comodel_name="hm.salary.rule",
        inverse_name="structure_id",
        string="Salary Rules",
        copy=True,
    )
    note = fields.Text(string="Description")


class HmSalaryRule(models.Model):
    _name = "hm.salary.rule"
    _description = "Salary Rule"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(
        required=True,
        help="Rule codes name the payslip lines. They must be unique within "
             "the structure.",
    )
    sequence = fields.Integer(
        default=100,
        required=True,
        help="Rules run in sequence order, and each one sees only the "
             "category totals of the rules that ran before it.",
    )
    active = fields.Boolean(default=True)
    structure_id = fields.Many2one(
        comodel_name="hm.payroll.structure",
        string="Structure",
        required=True,
        ondelete="cascade",
        index=True,
    )
    category_id = fields.Many2one(
        comodel_name="hm.salary.rule.category",
        string="Category",
        required=True,
        help="The line's total accumulates into this category, where later "
             "rules can read it.",
    )
    appears_on_payslip = fields.Boolean(
        string="Appears on Payslip",
        default=True,
        help="Untick for intermediate rules that the employee should not "
             "see printed. The line is still computed and still counts "
             "toward its category.",
    )

    condition_select = fields.Selection(
        selection=[("always", "Always True"), ("python", "Python Expression")],
        string="Condition",
        default="always",
        required=True,
    )
    condition_python = fields.Text(
        string="Condition Expression",
        default="version.wage > 0",
        help="A Python expression. The rule applies when it is true. In "
             "scope: employee, version, payslip, categories, inputs.",
    )

    amount_select = fields.Selection(
        selection=[
            ("fix", "Fixed Amount"),
            ("percentage", "Percentage (%)"),
            ("code", "Python Code"),
        ],
        string="Amount Type",
        default="fix",
        required=True,
    )
    amount_fix = fields.Float(string="Fixed Amount")
    amount_percentage = fields.Float(
        string="Percentage (%)",
        help="May be negative: a deduction of ten percent is -10.",
    )
    amount_percentage_base = fields.Char(
        string="Percentage Based On",
        help="A Python expression giving the base, e.g. version.wage or "
             "categories['GROSS'].",
    )
    amount_python = fields.Text(
        string="Python Code",
        default=(
            "# Set result. Optionally result_qty and result_rate.\n"
            "result = version.wage"
        ),
        help="Python statements that set 'result' (the amount) and may set "
             "'result_qty' and 'result_rate'. The line total is "
             "quantity * amount * rate / 100. In scope: employee, version, "
             "payslip, categories, inputs.",
    )

    account_debit_id = fields.Many2one(
        comodel_name="account.account",
        string="Debit Account",
        help="The line's total is debited here; a negative total flips to "
             "the credit side. A deduction rule therefore books its "
             "liability by putting the payable account in this field.",
    )
    account_credit_id = fields.Many2one(
        comodel_name="account.account",
        string="Credit Account",
        help="The line's total is credited here; a negative total flips to "
             "the debit side.",
    )
    note = fields.Text(string="Description")

    _code_per_structure_uniq = models.Constraint(
        "unique(structure_id, code)",
        "Rule codes must be unique within a salary structure.",
    )

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def _satisfies_condition(self, localdict):
        self.ensure_one()
        if self.condition_select == "always":
            return True
        try:
            return bool(safe_eval(self.condition_python or "False", localdict))
        except Exception as err:
            raise UserError(
                _("Salary rule %(rule)s [%(code)s]: the condition could not "
                  "be evaluated.\n%(error)s")
                % {"rule": self.name, "code": self.code, "error": err}
            ) from err

    def _compute_amount(self, localdict):
        """Return (amount, quantity, rate) for one payslip line."""
        self.ensure_one()
        try:
            if self.amount_select == "fix":
                return self.amount_fix, 1.0, 100.0
            if self.amount_select == "percentage":
                base = float(
                    safe_eval(self.amount_percentage_base or "0.0", localdict)
                )
                return base, 1.0, self.amount_percentage
            # Odoo 19's safe_eval always mutates the context it is given
            # (the old nocopy parameter is gone), so 'result' lands straight
            # in localdict.
            safe_eval(self.amount_python or "", localdict, mode="exec")
            result = localdict.get("result")
            if result is None:
                raise UserError(
                    _("The code never set 'result'.")
                )
            return (
                float(result),
                float(localdict.get("result_qty", 1.0)),
                float(localdict.get("result_rate", 100.0)),
            )
        except UserError:
            raise
        except Exception as err:
            raise UserError(
                _("Salary rule %(rule)s [%(code)s]: the amount could not be "
                  "computed.\n%(error)s")
                % {"rule": self.name, "code": self.code, "error": err}
            ) from err
