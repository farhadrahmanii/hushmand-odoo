# Part of hm_assets. See LICENSE file for full copyright and licensing details.
"""Fixed assets and depreciation.

Odoo's asset management is Enterprise, so a Community user who buys a vehicle
has a bill and nothing else: no register, no depreciation, and a balance sheet
that overstates what the company owns for the rest of the asset's life.

This computes a depreciation schedule and posts it to the general ledger.

One deliberate choice runs through the whole model: **nothing posts by
itself**. The schedule is a forecast until someone confirms a period. Software
that quietly writes journal entries into a closed month is worse than software
that writes none.
"""

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class HmAsset(models.Model):
    _name = "hm.asset"
    _description = "Fixed Asset"
    _inherit = ["mail.thread", "mail.activity.mixin", "hm.license.gate"]
    _licence_module = "hm_assets"
    _order = "date_start desc, id desc"
    _check_company_auto = True

    name = fields.Char(string="Asset", required=True, tracking=True)
    code = fields.Char(string="Reference", copy=False, tracking=True)
    category_id = fields.Many2one(
        comodel_name="hm.asset.category",
        string="Category",
        tracking=True,
        check_company=True,
        help="Supplies the accounts and the default schedule.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id", readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner", string="Supplier",
    )

    # ------------------------------------------------------------------
    # Values
    # ------------------------------------------------------------------

    purchase_value = fields.Monetary(
        string="Purchase Value", required=True, tracking=True,
    )
    salvage_value = fields.Monetary(
        string="Salvage Value",
        tracking=True,
        help="What the asset is expected to be worth at the end. Never "
             "depreciated below this.",
    )
    depreciable_value = fields.Monetary(
        string="Depreciable", compute="_compute_depreciable_value", store=True,
    )
    depreciated_value = fields.Monetary(
        string="Depreciated So Far", compute="_compute_totals", store=True,
    )
    book_value = fields.Monetary(
        string="Book Value", compute="_compute_totals", store=True,
        help="Purchase value less everything posted to date.",
    )

    # ------------------------------------------------------------------
    # Schedule
    # ------------------------------------------------------------------

    date_start = fields.Date(
        string="In Service",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        help="Depreciation runs from this date, not the invoice date.",
    )
    method = fields.Selection(
        selection=[
            ("linear", "Straight line"),
            ("degressive", "Reducing balance"),
        ],
        default="linear",
        required=True,
        tracking=True,
    )
    method_progress_factor = fields.Float(
        string="Reducing Factor", default=0.3,
        help="Share of the remaining value written off each period.",
    )
    period_length = fields.Selection(
        selection=[("1", "Monthly"), ("3", "Quarterly"), ("12", "Yearly")],
        string="Period",
        default="12",
        required=True,
    )
    period_count = fields.Integer(
        string="Number of Periods", default=5, required=True,
    )
    prorata = fields.Boolean(
        string="Prorate First Period",
        default=True,
        help="Charge the first period only from the in-service date, rather "
             "than a full period for an asset bought on the last day.",
    )

    # ------------------------------------------------------------------
    # Accounts
    # ------------------------------------------------------------------

    account_asset_id = fields.Many2one(
        comodel_name="account.account",
        string="Asset Account",
        check_company=True,
        domain="[('account_type', 'in', ('asset_fixed', 'asset_non_current'))]",
    )
    account_depreciation_id = fields.Many2one(
        comodel_name="account.account",
        string="Accumulated Depreciation",
        check_company=True,
        help="Credited each period. Usually a negative asset account.",
    )
    account_expense_id = fields.Many2one(
        comodel_name="account.account",
        string="Depreciation Expense",
        check_company=True,
        domain="[('account_type', 'in', ('expense', 'expense_depreciation'))]",
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
        check_company=True,
        domain="[('type', '=', 'general')]",
    )

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("running", "Running"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )
    date_disposal = fields.Date(string="Disposed On", readonly=True, tracking=True)
    line_ids = fields.One2many(
        comodel_name="hm.asset.depreciation.line",
        inverse_name="asset_id",
        string="Depreciation",
    )
    posted_count = fields.Integer(compute="_compute_counts", string="Posted")
    pending_count = fields.Integer(compute="_compute_counts", string="Pending")

    _purchase_positive = models.Constraint(
        "CHECK (purchase_value > 0)",
        "The purchase value must be greater than zero.",
    )
    _periods_positive = models.Constraint(
        "CHECK (period_count > 0)",
        "An asset needs at least one depreciation period.",
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------

    @api.depends("purchase_value", "salvage_value")
    def _compute_depreciable_value(self):
        for asset in self:
            asset.depreciable_value = max(
                asset.purchase_value - asset.salvage_value, 0.0
            )

    # Split deliberately: depreciated_value and book_value are stored, the two
    # counts are not. Sharing one method means reading a count can trigger a
    # write to the stored values, which Odoo warns about.

    @api.depends("line_ids.amount", "line_ids.posted", "purchase_value")
    def _compute_totals(self):
        for asset in self:
            posted = asset.line_ids.filtered("posted")
            asset.depreciated_value = sum(posted.mapped("amount"))
            asset.book_value = asset.purchase_value - asset.depreciated_value

    @api.depends("line_ids.posted")
    def _compute_counts(self):
        for asset in self:
            posted = asset.line_ids.filtered("posted")
            asset.posted_count = len(posted)
            asset.pending_count = len(asset.line_ids) - len(posted)

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------

    @api.constrains("salvage_value", "purchase_value")
    def _check_salvage(self):
        for asset in self:
            if asset.salvage_value < 0:
                raise ValidationError(_("Salvage value cannot be negative."))
            if asset.salvage_value >= asset.purchase_value:
                raise ValidationError(
                    _("Salvage value must be below the purchase value, or "
                      "there is nothing to depreciate.")
                )

    @api.constrains("method_progress_factor", "method")
    def _check_factor(self):
        for asset in self:
            if asset.method == "degressive" and not 0 < asset.method_progress_factor < 1:
                raise ValidationError(
                    _("The reducing factor must be between 0 and 1.")
                )

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------

    @api.onchange("category_id")
    def _onchange_category(self):
        for asset in self:
            category = asset.category_id
            if not category:
                continue
            asset.method = category.method
            asset.method_progress_factor = category.method_progress_factor
            asset.period_length = category.period_length
            asset.period_count = category.period_count
            asset.prorata = category.prorata
            asset.account_asset_id = category.account_asset_id
            asset.account_depreciation_id = category.account_depreciation_id
            asset.account_expense_id = category.account_expense_id
            asset.journal_id = category.journal_id

    # ------------------------------------------------------------------
    # The schedule
    # ------------------------------------------------------------------

    def action_compute_depreciation(self):
        """Build the forecast. Posted periods are never touched."""
        for asset in self:
            if asset.state == "closed":
                raise UserError(
                    _("%s is closed.") % asset.display_name
                )
            asset.line_ids.filtered(lambda l: not l.posted).unlink()
            asset._generate_lines()
        return True

    def _generate_lines(self):
        self.ensure_one()
        currency = self.currency_id
        months = int(self.period_length)

        already = sum(self.line_ids.filtered("posted").mapped("amount"))
        remaining = self.depreciable_value - already
        if currency.compare_amounts(remaining, 0) <= 0:
            return

        posted_periods = len(self.line_ids.filtered("posted"))
        periods_left = self.period_count - posted_periods
        if periods_left <= 0:
            return

        # A prorated first period charges only the days actually in service,
        # and the remainder rolls into an extra period at the end.
        first_factor = 1.0
        if self.prorata and not posted_periods:
            first_factor = self._prorata_factor()

        values = []
        balance = remaining
        date = self._period_end(self.date_start, months, 0)

        for index in range(periods_left):
            if currency.is_zero(balance):
                break

            if self.method == "linear":
                base = remaining / periods_left
                amount = base * first_factor if index == 0 else base
            else:
                amount = (self.purchase_value - already
                          - sum(v["amount"] for v in values)) \
                    * self.method_progress_factor
                if index == 0:
                    amount *= first_factor

            # Never depreciate past the salvage value, and let the final
            # period absorb any rounding so the total lands exactly.
            if index == periods_left - 1 or currency.compare_amounts(amount, balance) > 0:
                amount = balance
            amount = currency.round(amount)
            if currency.is_zero(amount):
                break

            balance = currency.round(balance - amount)
            values.append({
                "asset_id": self.id,
                "sequence": posted_periods + index + 1,
                "date": date,
                "amount": amount,
                "remaining_value": balance + self.salvage_value,
            })
            date = self._period_end(self.date_start, months, index + 1)

        self.env["hm.asset.depreciation.line"].create(values)

    def _aligned_period_start(self):
        """Start of the calendar period the asset entered service in.

        Periods align to calendar boundaries -- the month, the quarter or the
        year containing the in-service date -- rather than starting on the
        asset's own date. Two reasons: a register is read against the
        company's periods, not each asset's anniversary, and prorata is
        meaningless otherwise. Aligning to the asset's own month made every
        asset start on day one of its first period, so the prorata factor was
        always exactly 1 and the option did nothing.
        """
        self.ensure_one()
        months = int(self.period_length)
        date = self.date_start

        if months == 12:
            return date.replace(month=1, day=1)
        if months == 3:
            quarter_month = ((date.month - 1) // 3) * 3 + 1
            return date.replace(month=quarter_month, day=1)
        return date.replace(day=1)

    def _prorata_factor(self):
        """The share of the first period the asset was actually in service."""
        self.ensure_one()
        months = int(self.period_length)
        period_start = self._aligned_period_start()
        period_end = period_start + relativedelta(months=months, days=-1)

        total_days = (period_end - period_start).days + 1
        in_service_days = (period_end - self.date_start).days + 1
        return max(min(in_service_days / total_days, 1.0), 0.0)

    def _period_end(self, start, months, index):
        """Last day of the depreciation period at ``index``."""
        first = self._aligned_period_start() + relativedelta(months=months * index)
        return first + relativedelta(months=months, days=-1)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def action_confirm(self):
        for asset in self:
            if asset.state != "draft":
                raise UserError(_("Only a draft asset can be confirmed."))
            asset._check_accounts()
            if not asset.line_ids:
                asset._generate_lines()
            asset.state = "running"

    def action_close(self):
        for asset in self:
            if asset.state != "running":
                raise UserError(_("Only a running asset can be closed."))
            asset.line_ids.filtered(lambda l: not l.posted).unlink()
            asset.write({
                "state": "closed",
                "date_disposal": fields.Date.context_today(asset),
            })
            asset.message_post(
                body=_("Closed with a book value of %s.")
                % asset.currency_id.format(asset.book_value)
            )

    def action_cancel(self):
        for asset in self:
            if asset.line_ids.filtered("posted"):
                raise UserError(
                    _("%s already has posted depreciation and cannot be "
                      "cancelled. Close it instead, so the entries stay.")
                    % asset.display_name
                )
            asset.line_ids.unlink()
            asset.state = "cancelled"

    def action_reset_draft(self):
        for asset in self:
            if asset.line_ids.filtered("posted"):
                raise UserError(
                    _("%s has posted entries. Returning it to draft would "
                      "detach them from the ledger.") % asset.display_name
                )
            asset.state = "draft"

    def _check_accounts(self):
        self.ensure_one()
        missing = [
            label for label, value in (
                (_("Asset Account"), self.account_asset_id),
                (_("Accumulated Depreciation"), self.account_depreciation_id),
                (_("Depreciation Expense"), self.account_expense_id),
                (_("Journal"), self.journal_id),
            ) if not value
        ]
        if missing:
            raise UserError(
                _("%(asset)s is missing: %(missing)s")
                % {"asset": self.display_name, "missing": ", ".join(missing)}
            )

    # ------------------------------------------------------------------
    # Views
    # ------------------------------------------------------------------

    def action_view_moves(self):
        self.ensure_one()
        moves = self.line_ids.mapped("move_id")
        return {
            "type": "ir.actions.act_window",
            "name": _("Depreciation Entries"),
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("id", "in", moves.ids)],
        }


class HmAssetCategory(models.Model):
    _name = "hm.asset.category"
    _description = "Asset Category"
    _order = "name"
    _check_company_auto = True

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    method = fields.Selection(
        selection=[
            ("linear", "Straight line"),
            ("degressive", "Reducing balance"),
        ],
        default="linear",
        required=True,
    )
    method_progress_factor = fields.Float(string="Reducing Factor", default=0.3)
    period_length = fields.Selection(
        selection=[("1", "Monthly"), ("3", "Quarterly"), ("12", "Yearly")],
        string="Period", default="12", required=True,
    )
    period_count = fields.Integer(string="Number of Periods", default=5, required=True)
    prorata = fields.Boolean(string="Prorate First Period", default=True)

    account_asset_id = fields.Many2one(
        comodel_name="account.account", string="Asset Account",
        check_company=True,
    )
    account_depreciation_id = fields.Many2one(
        comodel_name="account.account", string="Accumulated Depreciation",
        check_company=True,
    )
    account_expense_id = fields.Many2one(
        comodel_name="account.account", string="Depreciation Expense",
        check_company=True,
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal", string="Journal",
        check_company=True, domain="[('type', '=', 'general')]",
    )
    asset_count = fields.Integer(compute="_compute_asset_count")

    def _compute_asset_count(self):
        counts = dict(
            self.env["hm.asset"]._read_group(
                [("category_id", "in", self.ids)],
                groupby=["category_id"],
                aggregates=["__count"],
            )
        )
        for category in self:
            category.asset_count = counts.get(category, 0)
