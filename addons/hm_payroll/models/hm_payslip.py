# Part of hm_payroll. See LICENSE file for full copyright and licensing details.
"""Payslips, their lines, their inputs, and the batch that groups them.

The lifecycle is deliberate: **compute** builds the lines and writes nothing
anywhere else; **confirm** freezes the slip and creates a *draft* journal
entry; an accountant posts that entry; **mark paid** records that the money
went out. Nothing reaches the ledger without a person deciding it should.
"""

from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import date_utils, format_date


class HmPayslip(models.Model):
    _name = "hm.payslip"
    _description = "Payslip"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_to desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    number = fields.Char(
        string="Reference", readonly=True, copy=False, index=True,
    )
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Employee",
        required=True,
        tracking=True,
        index=True,
    )
    version_id = fields.Many2one(
        comodel_name="hr.version",
        string="Contract Version",
        compute="_compute_version",
        store=True,
        readonly=False,
        domain="[('employee_id', '=', employee_id)]",
        help="The contract version whose wage and terms the rules read. "
             "Defaults to the version in force during the payslip period, "
             "so a raise given in March does not rewrite January.",
    )
    structure_id = fields.Many2one(
        comodel_name="hm.payroll.structure",
        string="Salary Structure",
        required=True,
        tracking=True,
        domain="['|', ('company_id', '=', False),"
               " ('company_id', '=', company_id)]",
    )
    date_from = fields.Date(
        string="From",
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )
    date_to = fields.Date(
        string="To",
        required=True,
        default=lambda self: date_utils.end_of(
            fields.Date.context_today(self), "month"
        ),
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id", readonly=True,
    )
    run_id = fields.Many2one(
        comodel_name="hm.payslip.run",
        string="Batch",
        ondelete="set null",
        index="btree_not_null",
    )

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("done", "Confirmed"),
            ("paid", "Paid"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )
    line_ids = fields.One2many(
        comodel_name="hm.payslip.line",
        inverse_name="payslip_id",
        string="Lines",
    )
    input_line_ids = fields.One2many(
        comodel_name="hm.payslip.input",
        inverse_name="payslip_id",
        string="Other Inputs",
    )
    move_id = fields.Many2one(
        comodel_name="account.move",
        string="Journal Entry",
        readonly=True,
        copy=False,
        index="btree_not_null",
    )

    advance_line_ids = fields.One2many(
        comodel_name="hm.salary.advance.line",
        inverse_name="payslip_id",
        string="Advance Instalments",
        readonly=True,
    )
    advance_due = fields.Monetary(
        string="Advance Recovery",
        compute="_compute_advance_due",
        store=True,
        help="Advance instalments this payslip recovers. A deduction rule "
             "reads it as inputs.get('ADVANCE', 0.0).",
    )

    basic_wage = fields.Monetary(
        string="Basic", compute="_compute_summary", store=True,
    )
    gross_wage = fields.Monetary(
        string="Gross", compute="_compute_summary", store=True,
    )
    net_wage = fields.Monetary(
        string="Net", compute="_compute_summary", store=True,
    )
    notes = fields.Text()

    _dates_ordered = models.Constraint(
        "CHECK (date_from <= date_to)",
        "A payslip period cannot end before it starts.",
    )
    _number_uniq = models.Constraint(
        "unique(number, company_id)",
        "A payslip reference must be unique per company.",
    )

    # Frozen once the slip leaves draft. The form makes these readonly, but
    # a view attribute is a suggestion; this is the guarantee.
    _PROTECTED_AFTER_DRAFT = (
        "employee_id", "version_id", "structure_id",
        "date_from", "date_to", "company_id",
    )

    @api.constrains("company_id", "structure_id")
    def _check_company_consistency(self):
        for slip in self:
            structure_company = slip.structure_id.company_id
            if structure_company and structure_company != slip.company_id:
                raise ValidationError(
                    _("%(slip)s belongs to %(company)s but its salary "
                      "structure belongs to %(other)s. A payslip cannot "
                      "post into another company's books.")
                    % {
                        "slip": slip.display_name,
                        "company": slip.company_id.name,
                        "other": structure_company.name,
                    }
                )

    def write(self, vals):
        touched = [f for f in self._PROTECTED_AFTER_DRAFT if f in vals]
        if touched:
            frozen = self.filtered(lambda s: s.state != "draft")
            if frozen:
                raise UserError(
                    _("%(slips)s left draft; the employee, structure and "
                      "period are frozen. Reset to draft to change them.")
                    % {"slips": ", ".join(frozen.mapped("display_name"))}
                )
        return super().write(vals)

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------

    @api.depends("employee_id", "date_to")
    def _compute_name(self):
        for slip in self:
            if slip.employee_id and slip.date_to:
                slip.name = _("Salary Slip of %(employee)s for %(month)s") % {
                    "employee": slip.employee_id.name,
                    "month": format_date(
                        self.env, slip.date_to, date_format="MMMM y"
                    ),
                }
            else:
                slip.name = _("Salary Slip")

    @api.depends("employee_id", "date_to")
    def _compute_version(self):
        """The version in force at the end of the period, not today's.

        hr.version is a dated timeline precisely so that amendments keep
        their history; a January payslip computed after a March raise must
        still read January's wage.
        """
        for slip in self:
            if not slip.employee_id:
                slip.version_id = False
                continue
            date = slip.date_to or fields.Date.context_today(slip)
            slip.version_id = slip.employee_id._get_version(date)

    @api.depends("line_ids.total", "line_ids.category_id.code")
    def _compute_summary(self):
        for slip in self:
            totals = defaultdict(float)
            for line in slip.line_ids:
                totals[line.category_id.code] += line.total
            slip.basic_wage = totals.get("BASIC", 0.0)
            slip.gross_wage = totals.get("GROSS", 0.0)
            slip.net_wage = totals.get("NET", 0.0)

    @api.onchange("employee_id")
    def _onchange_employee(self):
        for slip in self:
            if slip.employee_id and not slip.structure_id:
                structures = self.env["hm.payroll.structure"].search(
                    [("company_id", "in", [self.env.company.id, False])]
                )
                structure_type = slip.version_id.structure_type_id
                slip.structure_id = (
                    structures.filtered(
                        lambda s: s.type_id == structure_type
                    )[:1]
                    or structures[:1]
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("number"):
                vals["number"] = (
                    self.env["ir.sequence"].next_by_code("hm.payslip") or "/"
                )
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Computation
    # ------------------------------------------------------------------

    def action_compute_sheet(self):
        for slip in self:
            if slip.state != "draft":
                raise UserError(
                    _("%s is not a draft. Only a draft payslip can be "
                      "recomputed.") % slip.display_name
                )
            if not slip.version_id:
                raise UserError(
                    _("%s has no contract version to read the wage from.")
                    % slip.employee_id.name
                )
            slip._claim_advance_instalments()
            slip.line_ids.unlink()
            slip.write({
                "line_ids": [(0, 0, vals) for vals in slip._compute_lines()],
            })
        return True

    # ------------------------------------------------------------------
    # Salary advances
    # ------------------------------------------------------------------

    def _claim_advance_instalments(self):
        """Take hold of the advance instalments this payslip will recover.

        Claiming happens at compute rather than at confirm so that two draft
        payslips for one employee cannot both plan to recover the same
        instalment. Recomputing releases what this payslip held and claims
        again, so a change of period is honoured.
        """
        self.ensure_one()
        self.advance_line_ids.filtered(lambda l: not l.recovered).write(
            {"payslip_id": False}
        )
        due = self.env["hm.salary.advance"]._instalments_due(
            self.employee_id, self.date_to, self.company_id
        )
        due.write({"payslip_id": self.id})

    def _release_advance_instalments(self):
        """Give back instalments this payslip was holding or had recovered."""
        for slip in self:
            slip.advance_line_ids.write(
                {"recovered": False, "payslip_id": False}
            )

    @api.depends("advance_line_ids.amount")
    def _compute_advance_due(self):
        for slip in self:
            slip.advance_due = sum(slip.advance_line_ids.mapped("amount"))

    def _rule_eval_context(self, categories, inputs):
        """What a salary rule can see when it is evaluated.

        Rule code is written by a payroll manager, but evaluated by whichever
        officer computes the slip -- and the wage field is HR-manager-gated.
        The records are elevated only inside the evaluation context, never
        handed back to the caller.

        Localization modules extend this to hand rules a helper rather than
        making every customer paste a tax formula into a text field. The
        Afghan payroll module adds an income-tax function this way.
        """
        self.ensure_one()
        return {
            "employee": self.employee_id.sudo(),
            "version": self.version_id.sudo(),
            "payslip": self,
            "categories": categories,
            "inputs": inputs,
        }

    def _compute_lines(self):
        """Run the structure's rules in order and return line values.

        Each rule sees ``categories``, the running totals of everything
        computed before it -- the ordering is the arithmetic.
        """
        self.ensure_one()
        categories = defaultdict(float)
        inputs = {
            line.code: line.amount
            for line in self.input_line_ids
            if line.code
        }
        # Advance instalments claimed by this payslip reach rules under a
        # reserved code, so a deduction rule is written the same way as any
        # other: -inputs.get("ADVANCE", 0.0). An input line typed by hand
        # under the same code wins, which is the manual override.
        inputs.setdefault("ADVANCE", self.advance_due)
        localdict = self._rule_eval_context(categories, inputs)
        vals_list = []
        rules = self.structure_id.rule_ids.filtered("active").sorted(
            key=lambda r: (r.sequence, r.id)
        )
        for rule in rules:
            localdict.update(
                {"result": None, "result_qty": 1.0, "result_rate": 100.0}
            )
            if not rule._satisfies_condition(localdict):
                continue
            amount, quantity, rate = rule._compute_amount(localdict)
            # Rounded here so the category totals later rules read agree to
            # the cent with the stored lines -- otherwise a NET computed
            # from categories can differ from the sum of its parts and the
            # journal entry fails at posting time.
            total = self.currency_id.round(quantity * amount * rate / 100.0)
            categories[rule.category_id.code] += total
            vals_list.append({
                "rule_id": rule.id,
                "sequence": rule.sequence,
                "code": rule.code,
                "name": rule.name,
                "category_id": rule.category_id.id,
                "quantity": quantity,
                "rate": rate,
                "amount": amount,
            })
        return vals_list

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------

    def action_confirm(self):
        for slip in self:
            if slip.state != "draft":
                raise UserError(
                    _("Only a draft payslip can be confirmed.")
                )
            if not slip.line_ids:
                raise UserError(
                    _("Compute %s before confirming it.") % slip.display_name
                )
            move = slip._create_move()
            slip.write({
                "state": "done",
                "move_id": move.id if move else False,
            })
            # The money is now genuinely taken off the employee's pay, so
            # the instalments this payslip was holding are recovered.
            slip.advance_line_ids.write({"recovered": True})
            slip.advance_line_ids.advance_id._refresh_state()
        return True

    def _create_move(self):
        """Create the draft journal entry, aggregated per account.

        Each line's total goes to its rule's debit account as a debit and to
        its credit account as a credit; a negative total flips the side. If
        no rule carries an account the slip posts nothing, and if the
        configured accounts do not balance the confirmation is refused --
        an unbalanced payroll entry is a configuration error, not something
        to paper over with a plug account.
        """
        self.ensure_one()
        currency = self.currency_id
        debit_totals = defaultdict(float)
        credit_totals = defaultdict(float)
        for line in self.line_ids:
            if currency.is_zero(line.total):
                continue
            rule = line.rule_id
            if rule.account_debit_id:
                debit_totals[rule.account_debit_id.id] += line.total
            if rule.account_credit_id:
                credit_totals[rule.account_credit_id.id] += line.total

        if not debit_totals and not credit_totals:
            return False
        journal = self.structure_id.journal_id.sudo()
        if not journal:
            raise UserError(
                _("%(structure)s has salary rules with accounts but no "
                  "salary journal. Set the journal on the structure.")
                % {"structure": self.structure_id.name}
            )
        if journal.company_id != self.company_id:
            raise UserError(
                _("The salary journal %(journal)s belongs to %(other)s, "
                  "not to %(company)s. A payslip cannot post into another "
                  "company's books.")
                % {
                    "journal": journal.name,
                    "other": journal.company_id.name,
                    "company": self.company_id.name,
                }
            )

        debit_sum = sum(debit_totals.values())
        credit_sum = sum(credit_totals.values())
        if currency.compare_amounts(debit_sum, credit_sum) != 0:
            raise UserError(
                _("The journal entry for %(slip)s does not balance: "
                  "%(debit)s to debit against %(credit)s to credit. Check "
                  "the debit and credit accounts on the structure's rules.")
                % {
                    "slip": self.display_name,
                    "debit": currency.format(debit_sum),
                    "credit": currency.format(credit_sum),
                }
            )

        label = _("Payroll: %(number)s (%(employee)s)") % {
            "number": self.number, "employee": self.employee_id.name,
        }
        line_vals = []
        for account_id, amount in debit_totals.items():
            amount = currency.round(amount)
            if currency.is_zero(amount):
                continue
            line_vals.append((0, 0, {
                "name": label,
                "account_id": account_id,
                "debit": amount if amount > 0 else 0.0,
                "credit": -amount if amount < 0 else 0.0,
            }))
        for account_id, amount in credit_totals.items():
            amount = currency.round(amount)
            if currency.is_zero(amount):
                continue
            line_vals.append((0, 0, {
                "name": label,
                "account_id": account_id,
                "debit": -amount if amount < 0 else 0.0,
                "credit": amount if amount > 0 else 0.0,
            }))
        # Confirming a payslip is payroll work, not accounting work: the
        # officer's right to do it is the payslip ACL, and the resulting
        # entry is a draft an accountant still has to post. Created with
        # sudo so a payroll officer without journal rights is not blocked.
        return self.env["account.move"].sudo().create({
            "move_type": "entry",
            "journal_id": journal.id,
            "date": self.date_to,
            "ref": self.number,
            "company_id": self.company_id.id,
            "line_ids": line_vals,
        })

    def action_mark_paid(self):
        for slip in self:
            if slip.state != "done":
                raise UserError(
                    _("Only a confirmed payslip can be marked paid.")
                )
            slip.state = "paid"
        return True

    def action_cancel(self):
        for slip in self:
            move = slip.move_id.sudo()
            if move and move.state == "posted":
                raise UserError(
                    _("The journal entry for %s is posted. Reverse it "
                      "first, so the ledger keeps a record of both.")
                    % slip.display_name
                )
            if move:
                move.unlink()
            # The deduction never happened, so the advance is owed again.
            advances = slip.advance_line_ids.advance_id
            slip._release_advance_instalments()
            advances._refresh_state()
            slip.state = "cancelled"
        return True

    def action_reset_draft(self):
        for slip in self:
            if slip.state != "cancelled":
                raise UserError(
                    _("Only a cancelled payslip can go back to draft.")
                )
            slip.state = "draft"
        return True

    def unlink(self):
        for slip in self:
            if slip.state not in ("draft", "cancelled"):
                raise UserError(
                    _("%s is confirmed. Cancel it before deleting it.")
                    % slip.display_name
                )
        # Deleting a draft payslip must not take its claim on an advance
        # with it, or the instalment becomes unrecoverable.
        self._release_advance_instalments()
        return super().unlink()


class HmPayslipLine(models.Model):
    _name = "hm.payslip.line"
    _description = "Payslip Line"
    _order = "sequence, id"

    payslip_id = fields.Many2one(
        comodel_name="hm.payslip",
        required=True,
        ondelete="cascade",
        index=True,
    )
    rule_id = fields.Many2one(
        comodel_name="hm.salary.rule",
        string="Rule",
        required=True,
        ondelete="restrict",
    )
    category_id = fields.Many2one(
        comodel_name="hm.salary.rule.category",
        string="Category",
        required=True,
    )
    sequence = fields.Integer(default=100)
    code = fields.Char(required=True)
    name = fields.Char(required=True)
    quantity = fields.Float(default=1.0)
    rate = fields.Float(string="Rate (%)", default=100.0)
    amount = fields.Monetary()
    total = fields.Monetary(compute="_compute_total", store=True)
    currency_id = fields.Many2one(
        related="payslip_id.currency_id", readonly=True,
    )
    appears_on_payslip = fields.Boolean(
        related="rule_id.appears_on_payslip", readonly=True,
    )

    @api.depends("quantity", "amount", "rate")
    def _compute_total(self):
        for line in self:
            total = line.quantity * line.amount * line.rate / 100.0
            currency = line.payslip_id.currency_id
            line.total = currency.round(total) if currency else total

    # The form shows lines readonly; this is the actual guarantee. The
    # engine only ever rebuilds lines while the slip is draft, so a guard
    # on the parent's state cannot get in its way.

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._check_payslip_is_draft()
        return records

    def write(self, vals):
        self._check_payslip_is_draft()
        return super().write(vals)

    def unlink(self):
        self._check_payslip_is_draft()
        return super().unlink()

    def _check_payslip_is_draft(self):
        for line in self:
            if line.payslip_id.state != "draft":
                raise UserError(
                    _("%s left draft; its lines are frozen. Reset the "
                      "payslip to draft first.")
                    % line.payslip_id.display_name
                )


class HmPayslipInput(models.Model):
    _name = "hm.payslip.input"
    _description = "Payslip Input"
    _order = "id"

    payslip_id = fields.Many2one(
        comodel_name="hm.payslip",
        required=True,
        ondelete="cascade",
        index=True,
    )
    name = fields.Char(required=True)
    code = fields.Char(
        required=True,
        help="How rules read this value, e.g. inputs.get('BONUS', 0.0).",
    )
    amount = fields.Monetary()
    currency_id = fields.Many2one(
        related="payslip_id.currency_id", readonly=True,
    )

    # Changing an input after confirmation would leave the stored lines
    # telling a different story from the inputs that produced them.

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._check_payslip_is_draft()
        return records

    def write(self, vals):
        self._check_payslip_is_draft()
        return super().write(vals)

    def unlink(self):
        self._check_payslip_is_draft()
        return super().unlink()

    def _check_payslip_is_draft(self):
        for record in self:
            if record.payslip_id.state != "draft":
                raise UserError(
                    _("%s left draft; its inputs are frozen. Reset the "
                      "payslip to draft first.")
                    % record.payslip_id.display_name
                )


class HmPayslipRun(models.Model):
    _name = "hm.payslip.run"
    _description = "Payslip Batch"
    _order = "date_to desc, id desc"

    name = fields.Char(required=True)
    structure_id = fields.Many2one(
        comodel_name="hm.payroll.structure",
        string="Salary Structure",
        required=True,
        domain="['|', ('company_id', '=', False),"
               " ('company_id', '=', company_id)]",
    )
    date_from = fields.Date(
        string="From",
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )
    date_to = fields.Date(
        string="To",
        required=True,
        default=lambda self: date_utils.end_of(
            fields.Date.context_today(self), "month"
        ),
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    state = fields.Selection(
        selection=[("draft", "Draft"), ("closed", "Closed")],
        default="draft",
        required=True,
        index=True,
    )
    slip_ids = fields.One2many(
        comodel_name="hm.payslip",
        inverse_name="run_id",
        string="Payslips",
    )
    slip_count = fields.Integer(compute="_compute_slip_count")

    _dates_ordered = models.Constraint(
        "CHECK (date_from <= date_to)",
        "A batch period cannot end before it starts.",
    )

    @api.constrains("company_id", "structure_id")
    def _check_company_consistency(self):
        for run in self:
            structure_company = run.structure_id.company_id
            if structure_company and structure_company != run.company_id:
                raise ValidationError(
                    _("%(run)s belongs to %(company)s but its salary "
                      "structure belongs to %(other)s.")
                    % {
                        "run": run.name,
                        "company": run.company_id.name,
                        "other": structure_company.name,
                    }
                )

    @api.depends("slip_ids")
    def _compute_slip_count(self):
        for run in self:
            run.slip_count = len(run.slip_ids)

    def action_open_generate(self):
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("%s is closed.") % self.name)
        return {
            "type": "ir.actions.act_window",
            "name": _("Generate Payslips"),
            "res_model": "hm.payslip.generate",
            "view_mode": "form",
            "target": "new",
            "context": {"default_run_id": self.id},
        }

    def action_confirm_all(self):
        for run in self:
            drafts = run.slip_ids.filtered(lambda s: s.state == "draft")
            if not drafts:
                raise UserError(
                    _("%s has no draft payslips to confirm.") % run.name
                )
            drafts.action_confirm()
        return True

    def action_close(self):
        for run in self:
            if any(slip.state == "draft" for slip in run.slip_ids):
                raise UserError(
                    _("Confirm or cancel every payslip in %s before closing "
                      "it.") % run.name
                )
            run.state = "closed"
        return True
