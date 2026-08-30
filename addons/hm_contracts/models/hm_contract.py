# Part of hm_contracts. See LICENSE file for full copyright and licensing details.
"""Recurring service contracts.

Odoo Subscriptions is Enterprise. A Community user with a maintenance
agreement, a security contract or an office lease has an invoice they remember
to raise, or forget to.

The model is a contract that knows when it is next due and can produce the
invoice. What it deliberately does not do is post anything on its own: it
raises the draft and tells somebody. Recurring billing that invoices silently
is how a customer receives a bill for a service that stopped three months ago.
"""

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

#: Recurrence in months, so every interval divides a year cleanly.
RECURRENCE = [
    ("1", "Monthly"),
    ("3", "Quarterly"),
    ("6", "Every Six Months"),
    ("12", "Yearly"),
]


class HmContract(models.Model):
    _name = "hm.contract"
    _description = "Service Contract"
    _inherit = ["mail.thread", "mail.activity.mixin", "hm.license.gate"]
    _licence_module = "hm_contracts"
    _order = "date_start desc, id desc"
    _check_company_auto = True

    name = fields.Char(
        string="Reference", required=True, copy=False, readonly=True,
        default=lambda self: _("New"),
    )
    title = fields.Char(
        string="Contract", required=True, tracking=True,
        help="What the contract is for, in the customer's language.",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
        required=True,
        tracking=True,
        index=True,
        check_company=True,
    )
    contract_type = fields.Selection(
        selection=[
            ("customer", "We Provide"),
            ("supplier", "We Receive"),
        ],
        default="customer",
        required=True,
        tracking=True,
        help="Whether this contract bills a customer or is billed by a "
             "supplier. Both are worth tracking; only one produces invoices.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id", readonly=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        default=lambda self: self.env.user,
        tracking=True,
    )

    # ------------------------------------------------------------------
    # Term
    # ------------------------------------------------------------------

    date_start = fields.Date(
        string="Starts", required=True, default=fields.Date.context_today,
        tracking=True,
    )
    date_end = fields.Date(
        string="Ends", tracking=True,
        help="Leave empty for an open-ended contract.",
    )
    recurrence = fields.Selection(
        selection=RECURRENCE, string="Billed", default="1", required=True,
        tracking=True,
    )
    date_next_invoice = fields.Date(
        string="Next Invoice",
        tracking=True,
        help="When the next invoice is due to be raised.",
    )
    auto_renew = fields.Boolean(
        string="Renews Automatically",
        help="Extends the end date by one term when it is reached, rather "
             "than expiring.",
    )
    notice_days = fields.Integer(
        string="Notice Period",
        default=30,
        help="Days before the end date to raise a reminder, so a renewal or "
             "termination decision is not made late.",
    )

    # ------------------------------------------------------------------
    # Money
    # ------------------------------------------------------------------

    line_ids = fields.One2many(
        comodel_name="hm.contract.line",
        inverse_name="contract_id",
        string="Lines",
        copy=True,
    )
    amount_recurring = fields.Monetary(
        string="Per Period", compute="_compute_amount", store=True,
    )
    amount_annual = fields.Monetary(
        string="Annualised", compute="_compute_amount", store=True,
        help="What the contract is worth over a year, so contracts on "
             "different cycles can be compared.",
    )

    invoice_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="hm_contract_id",
        string="Invoices",
        readonly=True,
    )
    invoice_count = fields.Integer(compute="_compute_invoice_count")

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("running", "Running"),
            ("expiring", "Expiring"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
        index=True,
        help="Draft, running, closed and cancelled are set deliberately. "
             "Expiring is derived from the end date by _refresh_state, which "
             "the daily job calls -- it cannot be a computed field, because "
             "the derivation has to read the current state to know whether a "
             "contract is eligible at all.",
    )
    notes = fields.Text()
    reminder_sent = fields.Boolean(readonly=True, copy=False)

    _dates_in_order = models.Constraint(
        "CHECK (date_end IS NULL OR date_start <= date_end)",
        "A contract cannot end before it starts.",
    )
    _notice_not_negative = models.Constraint(
        "CHECK (notice_days >= 0)",
        "The notice period cannot be negative.",
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------

    @api.depends("line_ids.subtotal", "recurrence")
    def _compute_amount(self):
        for contract in self:
            per_period = sum(contract.line_ids.mapped("subtotal"))
            months = int(contract.recurrence or "1")
            contract.amount_recurring = per_period
            contract.amount_annual = per_period * (12.0 / months)

    def _compute_invoice_count(self):
        counts = dict(self.env["account.move"]._read_group(
            [("hm_contract_id", "in", self.ids)],
            groupby=["hm_contract_id"], aggregates=["__count"],
        ))
        for contract in self:
            contract.invoice_count = counts.get(contract, 0)

    def _refresh_state(self):
        """Move a live contract between running, expiring and closed.

        Not a computed field. The rule reads the current state to decide
        whether a contract is eligible at all, so a compute would have to
        depend on itself. It is called by the daily job and whenever the end
        date changes.
        """
        today = fields.Date.context_today(self)
        for contract in self:
            if contract.state in ("draft", "closed", "cancelled"):
                continue
            if not contract.date_end:
                contract.state = "running"
                continue
            days_left = (contract.date_end - today).days
            if days_left < 0:
                contract.state = "closed"
            elif days_left <= (contract.notice_days or 0):
                contract.state = "expiring"
            else:
                contract.state = "running"

    @api.depends("name", "title", "partner_id")
    def _compute_display_name(self):
        for contract in self:
            contract.display_name = "%s - %s" % (
                contract.name or "", contract.title or ""
            )

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "hm.contract"
                ) or _("New")
        return super().create(vals_list)

    def write(self, vals):
        result = super().write(vals)
        # A changed term can move a contract into or out of "expiring", and
        # waiting for tomorrow's job to notice would be wrong on screen now.
        if {"date_end", "notice_days"} & set(vals):
            self.filtered(
                lambda c: c.state in ("running", "expiring")
            )._refresh_state()
        return result

    @api.constrains("line_ids", "state")
    def _check_has_lines_when_running(self):
        for contract in self:
            if contract.state == "running" and not contract.line_ids:
                raise ValidationError(
                    _("%s has nothing on it to bill.") % contract.name
                )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def action_start(self):
        for contract in self:
            if contract.state != "draft":
                raise UserError(_("Only a draft contract can be started."))
            if not contract.line_ids:
                raise UserError(
                    _("Add at least one line to %s first.") % contract.name
                )
            contract.write({
                "state": "running",
                "date_next_invoice": (
                    contract.date_next_invoice or contract.date_start
                ),
            })

    def action_close(self):
        for contract in self:
            if contract.state in ("closed", "cancelled"):
                raise UserError(_("%s is already closed.") % contract.name)
            contract.write({
                "state": "closed",
                "date_end": contract.date_end or fields.Date.context_today(contract),
            })

    def action_cancel(self):
        for contract in self:
            if contract.invoice_ids:
                raise UserError(
                    _("%s has been invoiced and cannot be cancelled. Close it "
                      "instead, so the invoices keep their contract.")
                    % contract.name
                )
            contract.state = "cancelled"

    def action_reset_draft(self):
        for contract in self:
            if contract.invoice_ids:
                raise UserError(
                    _("%s has invoices raised against it.") % contract.name
                )
            contract.state = "draft"

    def action_renew(self):
        """Extend by one term."""
        for contract in self:
            if not contract.date_end:
                raise UserError(
                    _("%s is open-ended and does not need renewing.")
                    % contract.name
                )
            months = int(contract.recurrence)
            contract.write({
                "date_end": contract.date_end + relativedelta(months=months),
                "state": "running",
                "reminder_sent": False,
            })
            contract.message_post(
                body=_("Renewed to %s.") % contract.date_end
            )

    # ------------------------------------------------------------------
    # Invoicing
    # ------------------------------------------------------------------

    def action_create_invoice(self):
        """Raise the next invoice as a draft, for someone to check and post."""
        invoices = self.env["account.move"]
        for contract in self:
            invoices |= contract._create_invoice()
        if not invoices:
            raise UserError(_("Nothing was due."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Invoices"),
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("id", "in", invoices.ids)],
        }

    def _create_invoice(self):
        self.ensure_one()
        if self.contract_type != "customer":
            raise UserError(
                _("%s is a supplier contract and does not raise invoices.")
                % self.name
            )
        if self.state not in ("running", "expiring"):
            raise UserError(
                _("%s is not running.") % self.name
            )
        if not self.line_ids:
            raise UserError(_("%s has nothing to bill.") % self.name)

        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "company_id": self.company_id.id,
            "invoice_date": self.date_next_invoice or fields.Date.context_today(self),
            "invoice_origin": self.name,
            "hm_contract_id": self.id,
            "invoice_line_ids": [
                (0, 0, line._prepare_invoice_line()) for line in self.line_ids
            ],
        })
        self._advance_next_invoice()
        self.message_post(
            body=_("Draft invoice %s raised.") % move.display_name
        )
        return move

    def action_view_invoices(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Invoices"),
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("hm_contract_id", "=", self.id)],
        }

    def _advance_next_invoice(self):
        self.ensure_one()
        base = self.date_next_invoice or fields.Date.context_today(self)
        self.date_next_invoice = base + relativedelta(months=int(self.recurrence))

    # ------------------------------------------------------------------
    # The daily job
    # ------------------------------------------------------------------

    @api.model
    def _cron_contracts(self):
        """Refresh statuses, raise renewal reminders, flag what is due.

        Nothing is invoiced here. A draft raised by a machine at 3am that
        nobody reads is how a customer gets billed for a service that stopped
        months ago; the job asks a person instead.
        """
        today = fields.Date.context_today(self)

        live = self.search([("state", "in", ("running", "expiring"))])
        live._refresh_state()

        # Renewal decisions coming up.
        for contract in live.filtered(
            lambda c: c.state == "expiring" and not c.reminder_sent
        ):
            if contract.auto_renew:
                contract.action_renew()
                continue
            if contract.user_id:
                contract.sudo().activity_schedule(
                    user_id=contract.user_id.id,
                    date_deadline=contract.date_end,
                    summary=_("Contract ending: %s") % contract.title,
                    note=_(
                        "%(contract)s with %(partner)s ends on %(date)s. "
                        "Renew it or let it lapse."
                    ) % {
                        "contract": contract.name,
                        "partner": contract.partner_id.display_name,
                        "date": contract.date_end,
                    },
                )
            contract.reminder_sent = True

        # Invoices now due.
        due = self.search([
            ("state", "in", ("running", "expiring")),
            ("contract_type", "=", "customer"),
            ("date_next_invoice", "<=", today),
        ])
        for contract in due:
            if not contract.user_id:
                continue
            contract.sudo().activity_schedule(
                user_id=contract.user_id.id,
                summary=_("Invoice due: %s") % contract.title,
                note=_(
                    "%(contract)s is due to be invoiced for the period "
                    "beginning %(date)s."
                ) % {
                    "contract": contract.name,
                    "date": contract.date_next_invoice,
                },
            )
        return len(due)


class HmContractLine(models.Model):
    _name = "hm.contract.line"
    _description = "Contract Line"
    _order = "contract_id, sequence, id"

    contract_id = fields.Many2one(
        comodel_name="hm.contract",
        string="Contract",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        help="Optional. A contract line can describe a service that is not a "
             "catalogue product.",
    )
    name = fields.Char(string="Description", required=True)
    quantity = fields.Float(string="Quantity", default=1.0, required=True)
    price_unit = fields.Float(string="Unit Price", digits="Product Price")
    subtotal = fields.Monetary(
        string="Subtotal", compute="_compute_subtotal", store=True,
    )
    currency_id = fields.Many2one(
        related="contract_id.currency_id", readonly=True,
    )
    account_id = fields.Many2one(
        comodel_name="account.account",
        string="Account",
        help="Leave empty to let Odoo choose from the product or the journal.",
    )
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account", string="Budget Line",
    )

    _quantity_positive = models.Constraint(
        "CHECK (quantity > 0)",
        "A contract line needs a quantity greater than zero.",
    )

    @api.depends("quantity", "price_unit")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit

    @api.onchange("product_id")
    def _onchange_product(self):
        for line in self:
            if not line.product_id:
                continue
            if not line.name:
                line.name = line.product_id.display_name
            if not line.price_unit:
                line.price_unit = line.product_id.list_price

    def _prepare_invoice_line(self):
        self.ensure_one()
        values = {
            "name": self.name,
            "quantity": self.quantity,
            "price_unit": self.price_unit,
        }
        if self.product_id:
            values["product_id"] = self.product_id.id
        if self.account_id:
            values["account_id"] = self.account_id.id
        if self.analytic_account_id:
            values["analytic_distribution"] = {
                str(self.analytic_account_id.id): 100.0
            }
        return values


class AccountMove(models.Model):
    _inherit = "account.move"

    hm_contract_id = fields.Many2one(
        comodel_name="hm.contract",
        string="Contract",
        readonly=True,
        index="btree_not_null",
    )
