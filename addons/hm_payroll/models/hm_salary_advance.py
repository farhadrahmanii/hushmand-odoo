# Part of hm_payroll. See LICENSE file for full copyright and licensing details.
"""Salary advances, and their recovery from later payslips.

An advance is money paid to an employee before it is earned, recovered from
the payslips that follow. Two things make it worth modelling rather than
handling by hand: the recovery is spread over months and has to stop at
exactly the right time, and the employer needs to know at any moment what is
still owed.

The schedule mirrors the one in hm_assets deliberately -- an ordered list of
dated instalments, each of which is claimed by exactly one payslip. A payslip
claims its instalments when it is computed and recovers them when it is
confirmed, so two payslips can never take the same instalment twice, and
cancelling a payslip puts its instalments back.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HmSalaryAdvance(models.Model):
    _name = "hm.salary.advance"
    _description = "Salary Advance"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(
        string="Reference", readonly=True, copy=False, index=True,
        default=lambda self: _("New"),
    )
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Employee",
        required=True,
        tracking=True,
        index=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id", readonly=True,
    )
    date = fields.Date(
        string="Advanced On",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    amount = fields.Monetary(string="Amount", required=True, tracking=True)
    installments = fields.Integer(
        string="Recover Over",
        default=1,
        required=True,
        tracking=True,
        help="How many payslips the recovery is spread across. One means the "
             "whole advance comes off the next payslip.",
    )
    date_first_recovery = fields.Date(
        string="First Recovery",
        help="The month the first instalment is taken from. Defaults to the "
             "month after the advance was given.",
    )
    reason = fields.Text(string="Reason")

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("approved", "Approved"),
            ("done", "Recovered"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )
    line_ids = fields.One2many(
        comodel_name="hm.salary.advance.line",
        inverse_name="advance_id",
        string="Instalments",
    )
    amount_recovered = fields.Monetary(
        string="Recovered", compute="_compute_amounts", store=True,
    )
    amount_outstanding = fields.Monetary(
        string="Still Owed", compute="_compute_amounts", store=True,
    )

    _amount_positive = models.Constraint(
        "CHECK (amount > 0)",
        "An advance must be greater than zero.",
    )
    _installments_positive = models.Constraint(
        "CHECK (installments >= 1)",
        "An advance must be recovered over at least one payslip.",
    )

    @api.depends("amount", "line_ids.amount", "line_ids.recovered")
    def _compute_amounts(self):
        for advance in self:
            recovered = sum(
                advance.line_ids.filtered("recovered").mapped("amount")
            )
            advance.amount_recovered = recovered
            advance.amount_outstanding = advance.amount - recovered

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "hm.salary.advance"
                ) or _("New")
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Schedule
    # ------------------------------------------------------------------

    def _first_recovery_date(self):
        """The month the first instalment falls in."""
        self.ensure_one()
        if self.date_first_recovery:
            return self.date_first_recovery
        # The month after the advance was given: an advance handed over
        # mid-month is normally recovered from the following payroll.
        return fields.Date.add(self.date, months=1)

    def _build_schedule(self):
        """One dated instalment per month, the remainder on the last.

        Splitting by division alone loses fractions of a currency unit, and
        an advance that never quite finishes recovering is worse than a
        rounding difference on one line.
        """
        self.ensure_one()
        currency = self.currency_id
        count = self.installments
        each = currency.round(self.amount / count)
        start = self._first_recovery_date()

        vals_list = []
        allocated = 0.0
        for index in range(count):
            last = index == count - 1
            amount = currency.round(self.amount - allocated) if last else each
            allocated += amount
            vals_list.append({
                "advance_id": self.id,
                "sequence": index + 1,
                "date": fields.Date.add(start, months=index),
                "amount": amount,
            })
        return vals_list

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------

    def action_approve(self):
        for advance in self:
            if advance.state != "draft":
                raise UserError(
                    _("Only a draft advance can be approved.")
                )
            advance.line_ids.unlink()
            self.env["hm.salary.advance.line"].create(
                advance._build_schedule()
            )
            advance.state = "approved"
        return True

    def action_cancel(self):
        for advance in self:
            if advance.amount_recovered:
                raise UserError(
                    _("%(advance)s has already had %(amount)s recovered from "
                      "payslips. Cancel those payslips first, so the money "
                      "taken back is not lost from the record.")
                    % {
                        "advance": advance.name,
                        "amount": advance.currency_id.format(
                            advance.amount_recovered
                        ),
                    }
                )
            advance.line_ids.filtered(lambda l: l.payslip_id).write(
                {"payslip_id": False}
            )
            advance.state = "cancelled"
        return True

    def action_reset_draft(self):
        for advance in self:
            if advance.state != "cancelled":
                raise UserError(
                    _("Only a cancelled advance can go back to draft.")
                )
            advance.state = "draft"
        return True

    def _refresh_state(self):
        """Close an advance once nothing is left to recover."""
        for advance in self:
            if advance.state not in ("approved", "done"):
                continue
            fully = advance.line_ids and all(
                line.recovered for line in advance.line_ids
            )
            advance.state = "done" if fully else "approved"

    def unlink(self):
        for advance in self:
            if advance.state not in ("draft", "cancelled"):
                raise UserError(
                    _("%s is approved. Cancel it before deleting it.")
                    % advance.name
                )
        return super().unlink()

    # ------------------------------------------------------------------
    # What a payslip may take
    # ------------------------------------------------------------------

    @api.model
    def _instalments_due(self, employee, date_to, company):
        """Unclaimed instalments for this employee falling due by date_to.

        A line already claimed by another payslip is excluded, which is what
        stops the same instalment being recovered twice.
        """
        return self.env["hm.salary.advance.line"].search([
            ("advance_id.employee_id", "=", employee.id),
            ("advance_id.company_id", "=", company.id),
            ("advance_id.state", "in", ("approved", "done")),
            ("recovered", "=", False),
            ("payslip_id", "=", False),
            ("date", "<=", date_to),
        ], order="date, sequence, id")


class HmSalaryAdvanceLine(models.Model):
    _name = "hm.salary.advance.line"
    _description = "Salary Advance Instalment"
    _order = "date, sequence, id"

    advance_id = fields.Many2one(
        comodel_name="hm.salary.advance",
        required=True,
        ondelete="cascade",
        index=True,
    )
    employee_id = fields.Many2one(
        related="advance_id.employee_id", store=True, readonly=True,
    )
    company_id = fields.Many2one(
        related="advance_id.company_id", store=True, readonly=True,
    )
    currency_id = fields.Many2one(
        related="advance_id.currency_id", readonly=True,
    )
    sequence = fields.Integer(string="#", default=1)
    date = fields.Date(string="Due", required=True, index=True)
    amount = fields.Monetary(string="Amount", required=True)
    recovered = fields.Boolean(
        string="Recovered", default=False, index=True,
        help="Set when the payslip that took this instalment was confirmed.",
    )
    payslip_id = fields.Many2one(
        comodel_name="hm.payslip",
        string="Payslip",
        readonly=True,
        index="btree_not_null",
        help="The payslip that has claimed this instalment. Set while the "
             "payslip is still a draft, so no other payslip can take it.",
    )

    _amount_positive = models.Constraint(
        "CHECK (amount > 0)",
        "An instalment must be greater than zero.",
    )

    def unlink(self):
        if any(line.recovered for line in self):
            raise UserError(
                _("An instalment already recovered from a payslip cannot be "
                  "deleted. Cancel the payslip instead.")
            )
        return super().unlink()
