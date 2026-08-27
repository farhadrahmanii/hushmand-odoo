# Part of af_zakat. See LICENSE file for full copyright and licensing details.
"""Zakat and charitable distribution.

Zakat is not an expense. It is an obligation calculated on wealth held for a
lunar year, collected into a fund, and distributed to people who qualify under
defined categories. An organisation administering it has to be able to show
what came in, who received what, and that the two reconcile -- to donors, to
beneficiaries, and to anyone who asks.

Odoo has no concept of this, and treating it as ordinary expenses loses the
part that matters: the link between a contribution and the distributions it
paid for.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

#: The eight categories of eligible recipient named in the Qur'an (9:60).
#: Fixed rather than configurable, because they are not a matter of local
#: preference -- an organisation may not use all of them, but it does not get
#: to invent a ninth.
BENEFICIARY_CATEGORIES = [
    ("faqir", "Faqir (the poor)"),
    ("miskin", "Miskin (the needy)"),
    ("amil", "Amil (administrators of zakat)"),
    ("muallaf", "Muallaf (those whose hearts are to be reconciled)"),
    ("riqab", "Riqab (freeing those in bondage)"),
    ("gharim", "Gharim (those in debt)"),
    ("fisabilillah", "Fi Sabilillah (in the cause of God)"),
    ("ibnsabil", "Ibn al-Sabil (the traveller in need)"),
]


class AfZakatFund(models.Model):
    _name = "af.zakat.fund"
    _description = "Zakat Fund"
    _inherit = ["mail.thread"]
    _order = "date_from desc, id desc"

    name = fields.Char(required=True, tracking=True)
    date_from = fields.Date(string="From", required=True, tracking=True)
    date_to = fields.Date(string="To", required=True, tracking=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id", readonly=True,
    )
    state = fields.Selection(
        selection=[
            ("open", "Open"),
            ("closed", "Closed"),
        ],
        default="open",
        required=True,
        tracking=True,
    )

    contribution_ids = fields.One2many(
        comodel_name="af.zakat.contribution",
        inverse_name="fund_id",
        string="Contributions",
    )
    distribution_ids = fields.One2many(
        comodel_name="af.zakat.distribution",
        inverse_name="fund_id",
        string="Distributions",
    )

    amount_collected = fields.Monetary(
        string="Collected", compute="_compute_amounts", store=True,
    )
    amount_distributed = fields.Monetary(
        string="Distributed", compute="_compute_amounts", store=True,
    )
    amount_remaining = fields.Monetary(
        string="Undistributed", compute="_compute_amounts", store=True,
        help="What is still held and owed to beneficiaries.",
    )
    beneficiary_count = fields.Integer(compute="_compute_amounts")
    notes = fields.Text()

    _dates_in_order = models.Constraint(
        "CHECK (date_from <= date_to)",
        "A fund cannot end before it starts.",
    )

    @api.depends(
        "contribution_ids.amount",
        "contribution_ids.state",
        "distribution_ids.amount",
        "distribution_ids.state",
    )
    def _compute_amounts(self):
        for fund in self:
            received = fund.contribution_ids.filtered(
                lambda c: c.state == "received"
            )
            paid = fund.distribution_ids.filtered(lambda d: d.state == "paid")
            fund.amount_collected = sum(received.mapped("amount"))
            fund.amount_distributed = sum(paid.mapped("amount"))
            fund.amount_remaining = (
                fund.amount_collected - fund.amount_distributed
            )
            fund.beneficiary_count = len(set(paid.mapped("beneficiary_id").ids))

    def action_close(self):
        """Close the fund, refusing to hide an undistributed balance."""
        for fund in self:
            if fund.state != "open":
                raise UserError(_("%s is already closed.") % fund.name)
            if fund.currency_id.compare_amounts(fund.amount_remaining, 0) > 0:
                raise UserError(
                    _("%(fund)s still holds %(amount)s that has not been "
                      "distributed. Distribute it or carry it into another "
                      "fund before closing this one.")
                    % {
                        "fund": fund.name,
                        "amount": fund.currency_id.format(fund.amount_remaining),
                    }
                )
            fund.state = "closed"

    def action_reopen(self):
        for fund in self:
            fund.state = "open"

    def action_view_distributions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Distributions"),
            "res_model": "af.zakat.distribution",
            "view_mode": "list,form",
            "domain": [("fund_id", "=", self.id)],
            "context": {"default_fund_id": self.id},
        }


class AfZakatContribution(models.Model):
    _name = "af.zakat.contribution"
    _description = "Zakat Contribution"
    _inherit = ["mail.thread"]
    _order = "date desc, id desc"

    name = fields.Char(
        string="Reference", required=True, copy=False, readonly=True,
        default=lambda self: _("New"),
    )
    fund_id = fields.Many2one(
        comodel_name="af.zakat.fund",
        string="Fund",
        required=True,
        ondelete="restrict",
        index=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Contributor",
        tracking=True,
    )
    anonymous = fields.Boolean(
        string="Anonymous",
        help="Zakat is often given without the giver being named. The record "
             "still exists; the name simply is not shown.",
    )
    date = fields.Date(
        string="Received", required=True, default=fields.Date.context_today,
        tracking=True,
    )
    amount = fields.Monetary(string="Amount", required=True, tracking=True)
    currency_id = fields.Many2one(
        related="fund_id.currency_id", readonly=True,
    )
    company_id = fields.Many2one(
        related="fund_id.company_id", store=True, readonly=True,
    )
    payment_method = fields.Selection(
        selection=[
            ("cash", "Cash"),
            ("bank", "Bank Transfer"),
            ("in_kind", "In Kind"),
        ],
        default="cash",
        required=True,
    )
    state = fields.Selection(
        selection=[
            ("pledged", "Pledged"),
            ("received", "Received"),
            ("cancelled", "Cancelled"),
        ],
        default="received",
        required=True,
        tracking=True,
        index=True,
        help="A pledge is not money. Only received contributions count "
             "towards what can be distributed.",
    )
    notes = fields.Text()

    _amount_positive = models.Constraint(
        "CHECK (amount > 0)",
        "A contribution must be greater than zero.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "af.zakat.contribution"
                ) or _("New")
        return super().create(vals_list)

    @api.depends("name", "partner_id", "anonymous")
    def _compute_display_name(self):
        for contribution in self:
            giver = (
                _("Anonymous") if contribution.anonymous
                else contribution.partner_id.display_name or ""
            )
            contribution.display_name = (
                "%s - %s" % (contribution.name, giver)
                if giver else contribution.name or ""
            )

    def action_mark_received(self):
        for contribution in self:
            contribution.state = "received"

    def action_cancel(self):
        for contribution in self:
            contribution.state = "cancelled"


class AfZakatBeneficiary(models.Model):
    _name = "af.zakat.beneficiary"
    _description = "Zakat Beneficiary"
    _inherit = ["mail.thread"]
    _order = "name"

    name = fields.Char(required=True, tracking=True)
    partner_id = fields.Many2one(
        comodel_name="res.partner", string="Contact",
    )
    category = fields.Selection(
        selection=BENEFICIARY_CATEGORIES,
        string="Category",
        required=True,
        tracking=True,
        help="Which of the eight eligible categories this person falls under.",
    )
    father_name = fields.Char(string="Father's Name")
    tazkira = fields.Char(string="Tazkira Number")
    phone = fields.Char()
    state_id = fields.Many2one(
        comodel_name="res.country.state", string="Province",
    )
    district_id = fields.Many2one(
        comodel_name="af.district", string="District",
    )
    address = fields.Char(string="Address")

    household_size = fields.Integer(
        string="Household",
        default=1,
        help="How many people depend on this person.",
    )
    assessment_notes = fields.Text(
        string="Assessment",
        help="Why this person qualifies, and who verified it.",
    )
    verified_by_id = fields.Many2one(
        comodel_name="res.users", string="Verified By", tracking=True,
    )
    verified_date = fields.Date(string="Verified On", tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )

    distribution_ids = fields.One2many(
        comodel_name="af.zakat.distribution",
        inverse_name="beneficiary_id",
        string="Distributions",
    )
    total_received = fields.Monetary(
        compute="_compute_totals", store=True,
        help="Across every fund, so repeat assistance is visible.",
    )
    distribution_count = fields.Integer(compute="_compute_totals", store=True)
    last_received = fields.Date(compute="_compute_totals", store=True)
    currency_id = fields.Many2one(
        related="company_id.currency_id", readonly=True,
    )

    _household_positive = models.Constraint(
        "CHECK (household_size > 0)",
        "A household has at least one person in it.",
    )

    @api.depends("distribution_ids.amount", "distribution_ids.state",
                 "distribution_ids.date")
    def _compute_totals(self):
        for beneficiary in self:
            paid = beneficiary.distribution_ids.filtered(
                lambda d: d.state == "paid"
            )
            beneficiary.total_received = sum(paid.mapped("amount"))
            beneficiary.distribution_count = len(paid)
            beneficiary.last_received = max(
                paid.mapped("date"), default=False
            )

    @api.depends("name", "father_name")
    def _compute_display_name(self):
        for beneficiary in self:
            beneficiary.display_name = (
                "%s s/o %s" % (beneficiary.name, beneficiary.father_name)
                if beneficiary.father_name else beneficiary.name or ""
            )


class AfZakatDistribution(models.Model):
    _name = "af.zakat.distribution"
    _description = "Zakat Distribution"
    _inherit = ["mail.thread"]
    _order = "date desc, id desc"

    name = fields.Char(
        string="Reference", required=True, copy=False, readonly=True,
        default=lambda self: _("New"),
    )
    fund_id = fields.Many2one(
        comodel_name="af.zakat.fund",
        string="Fund",
        required=True,
        ondelete="restrict",
        index=True,
    )
    beneficiary_id = fields.Many2one(
        comodel_name="af.zakat.beneficiary",
        string="Beneficiary",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    category = fields.Selection(
        related="beneficiary_id.category", store=True, readonly=True,
        string="Category",
    )
    date = fields.Date(
        string="Paid", required=True, default=fields.Date.context_today,
        tracking=True,
    )
    amount = fields.Monetary(string="Amount", required=True, tracking=True)
    currency_id = fields.Many2one(
        related="fund_id.currency_id", readonly=True,
    )
    company_id = fields.Many2one(
        related="fund_id.company_id", store=True, readonly=True,
    )
    payment_method = fields.Selection(
        selection=[
            ("cash", "Cash"),
            ("bank", "Bank Transfer"),
            ("in_kind", "In Kind"),
        ],
        default="cash",
        required=True,
    )
    in_kind_description = fields.Char(
        string="Goods Given",
        help="What was actually handed over, when it was not money.",
    )
    state = fields.Selection(
        selection=[
            ("planned", "Planned"),
            ("paid", "Paid"),
            ("cancelled", "Cancelled"),
        ],
        default="planned",
        required=True,
        tracking=True,
        index=True,
    )
    approved_by_id = fields.Many2one(
        comodel_name="res.users", string="Approved By", tracking=True,
    )
    received_signature = fields.Boolean(
        string="Receipt Signed",
        help="Whether the beneficiary signed for what they were given.",
    )
    notes = fields.Text()

    _amount_positive = models.Constraint(
        "CHECK (amount > 0)",
        "A distribution must be greater than zero.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "af.zakat.distribution"
                ) or _("New")
        return super().create(vals_list)

    @api.constrains("fund_id", "state")
    def _check_fund_open(self):
        for distribution in self:
            if (
                distribution.state != "cancelled"
                and distribution.fund_id.state == "closed"
            ):
                raise ValidationError(
                    _("%s is closed and cannot take further distributions.")
                    % distribution.fund_id.name
                )

    def action_mark_paid(self):
        """Pay, refusing to distribute money the fund does not hold."""
        for distribution in self:
            if distribution.state == "paid":
                raise UserError(
                    _("%s is already paid.") % distribution.name
                )
            fund = distribution.fund_id
            currency = fund.currency_id
            if currency.compare_amounts(
                distribution.amount, fund.amount_remaining
            ) > 0:
                raise UserError(
                    _("%(fund)s holds %(available)s undistributed, which is "
                      "less than %(amount)s. Zakat cannot be paid out of "
                      "money that has not been collected.")
                    % {
                        "fund": fund.name,
                        "available": currency.format(fund.amount_remaining),
                        "amount": currency.format(distribution.amount),
                    }
                )
            distribution.state = "paid"

    def action_cancel(self):
        for distribution in self:
            distribution.state = "cancelled"

    @api.depends("name", "beneficiary_id")
    def _compute_display_name(self):
        for distribution in self:
            distribution.display_name = "%s - %s" % (
                distribution.name or "",
                distribution.beneficiary_id.name or "",
            )
