# Part of af_procurement. See LICENSE file for full copyright and licensing details.
"""The Afghan procurement document set.

The chain an Afghan office runs is PRF, then quotations compared on a
comparative form, then a purchase order, then a goods received note. Odoo has
the middle of that: a quotation becomes an order becomes a receipt. What it has
no concept of is the **comparative form** -- the sheet that records which
suppliers were asked, what each quoted, and why the chosen one was chosen.

That sheet is the audit trail. A donor or an auditor asking "why this supplier"
is asking for exactly this document, and in most offices it lives in a folder
rather than the system.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class HmPurchaseRequest(models.Model):
    _inherit = "hm.purchase.request"

    af_comparative_ids = fields.One2many(
        comodel_name="af.comparative.form",
        inverse_name="request_id",
        string="Comparative Forms",
    )
    af_comparative_count = fields.Integer(
        compute="_compute_af_comparative_count", string="Comparisons",
    )

    def _compute_af_comparative_count(self):
        counts = dict(self.env["af.comparative.form"]._read_group(
            [("request_id", "in", self.ids)],
            groupby=["request_id"], aggregates=["__count"],
        ))
        for request in self:
            request.af_comparative_count = counts.get(request, 0)

    def action_af_create_comparative(self):
        """Open a comparative form seeded from this request."""
        self.ensure_one()
        if self.state not in ("to_approve", "approved"):
            raise UserError(
                _("%s has to be submitted before quotations are compared.")
                % self.name
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("Comparative Form"),
            "res_model": "af.comparative.form",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_request_id": self.id,
                "default_name": _("Comparison for %s") % self.name,
            },
        }

    def action_af_view_comparatives(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Comparative Forms"),
            "res_model": "af.comparative.form",
            "view_mode": "list,form",
            "domain": [("request_id", "=", self.id)],
            "context": {"default_request_id": self.id},
        }


class AfComparativeForm(models.Model):
    _name = "af.comparative.form"
    _description = "Comparative Form"
    _inherit = ["mail.thread"]
    _order = "date desc, id desc"

    name = fields.Char(required=True, tracking=True)
    reference = fields.Char(
        string="Reference", copy=False, readonly=True,
        default=lambda self: _("New"),
    )
    request_id = fields.Many2one(
        comodel_name="hm.purchase.request",
        string="Purchase Request",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        related="request_id.company_id", store=True, readonly=True,
    )
    currency_id = fields.Many2one(
        related="request_id.currency_id", readonly=True,
    )
    date = fields.Date(
        string="Date", required=True, default=fields.Date.context_today,
    )
    prepared_by_id = fields.Many2one(
        comodel_name="res.users",
        string="Prepared By",
        default=lambda self: self.env.user,
        tracking=True,
    )

    quote_ids = fields.One2many(
        comodel_name="af.comparative.quote",
        inverse_name="form_id",
        string="Quotations",
    )
    quote_count = fields.Integer(compute="_compute_quote_stats")
    lowest_quote_id = fields.Many2one(
        comodel_name="af.comparative.quote",
        string="Lowest",
        compute="_compute_quote_stats",
        help="The cheapest quotation. Not necessarily the one chosen.",
    )

    selected_quote_id = fields.Many2one(
        comodel_name="af.comparative.quote",
        string="Selected",
        tracking=True,
        domain="[('form_id', '=', id)]",
    )
    selection_reason = fields.Text(
        string="Reason for Selection",
        tracking=True,
        help="Required when the chosen quotation is not the cheapest. This is "
             "the sentence an auditor reads.",
    )
    not_lowest = fields.Boolean(
        compute="_compute_quote_stats",
        string="Not the Lowest",
    )

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("done", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )
    notes = fields.Text()

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------

    @api.depends("quote_ids.total_amount", "selected_quote_id")
    def _compute_quote_stats(self):
        for form in self:
            quotes = form.quote_ids.filtered(lambda q: q.total_amount > 0)
            form.quote_count = len(form.quote_ids)
            lowest = min(quotes, key=lambda q: q.total_amount) if quotes else False
            form.lowest_quote_id = lowest
            form.not_lowest = bool(
                form.selected_quote_id
                and lowest
                and form.selected_quote_id != lowest
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("reference", _("New")) == _("New"):
                vals["reference"] = self.env["ir.sequence"].next_by_code(
                    "af.comparative.form"
                ) or _("New")
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Rules
    # ------------------------------------------------------------------

    @api.constrains("selected_quote_id")
    def _check_selected_belongs_here(self):
        for form in self:
            if (
                form.selected_quote_id
                and form.selected_quote_id.form_id != form
            ):
                raise ValidationError(
                    _("The selected quotation belongs to another comparison.")
                )

    def action_done(self):
        """Complete the comparison.

        Two rules, and both exist because of what an auditor asks. There has
        to be more than one quotation, or nothing was compared. And if the
        chosen supplier is not the cheapest, the reason has to be written
        down at the time -- not reconstructed months later.
        """
        for form in self:
            if form.state != "draft":
                raise UserError(_("This comparison is already completed."))
            if len(form.quote_ids) < 2:
                raise UserError(
                    _("A comparison needs at least two quotations. With one, "
                      "nothing has been compared.")
                )
            if not form.selected_quote_id:
                raise UserError(
                    _("Choose the quotation you are recommending.")
                )
            if form.not_lowest and not (form.selection_reason or "").strip():
                raise UserError(
                    _("%(supplier)s is not the lowest quotation. Write down "
                      "why it was chosen -- that sentence is what an auditor "
                      "will ask for.")
                    % {"supplier": form.selected_quote_id.partner_id.display_name}
                )
            form.state = "done"
            form._post_summary()

    def _post_summary(self):
        self.ensure_one()
        chosen = self.selected_quote_id
        body = _("%(supplier)s selected at %(amount)s, from %(count)s "
                 "quotation(s).") % {
            "supplier": chosen.partner_id.display_name,
            "amount": self.currency_id.format(chosen.total_amount),
            "count": len(self.quote_ids),
        }
        if self.not_lowest:
            body += "<br/>" + _("Not the lowest. Reason: %s") % (
                self.selection_reason or ""
            )
        self.message_post(body=body)
        if self.request_id:
            self.request_id.message_post(body=body)

    def action_cancel(self):
        for form in self:
            if form.state == "done":
                raise UserError(
                    _("A completed comparison cannot be cancelled. It is part "
                      "of the record of how the supplier was chosen.")
                )
            form.state = "cancelled"

    def action_reset_draft(self):
        for form in self:
            if form.state != "cancelled":
                raise UserError(_("Only a cancelled comparison can be reset."))
            form.state = "draft"

    def action_apply_to_request(self):
        """Put the selected supplier onto the purchase request."""
        self.ensure_one()
        if self.state != "done":
            raise UserError(
                _("Complete the comparison before applying it.")
            )
        self.request_id.vendor_id = self.selected_quote_id.partner_id
        self.request_id.message_post(
            body=_("Supplier set from comparison %s.") % self.reference
        )
        return True


class AfComparativeQuote(models.Model):
    _name = "af.comparative.quote"
    _description = "Quotation on a Comparative Form"
    _order = "form_id, total_amount, id"

    form_id = fields.Many2one(
        comodel_name="af.comparative.form",
        string="Comparison",
        required=True,
        ondelete="cascade",
        index=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Supplier",
        required=True,
    )
    currency_id = fields.Many2one(
        related="form_id.currency_id", readonly=True,
    )
    quotation_ref = fields.Char(
        string="Quotation No.",
        help="The supplier's own reference, so the paper can be found again.",
    )
    quotation_date = fields.Date(string="Quoted On")
    total_amount = fields.Monetary(string="Total", required=True)
    delivery_days = fields.Integer(
        string="Delivery (days)",
        help="How long the supplier says it will take. Often the reason a "
             "dearer quotation is chosen.",
    )
    warranty_months = fields.Integer(string="Warranty (months)")
    payment_terms = fields.Char(string="Payment Terms")
    notes = fields.Char(string="Remarks")
    is_selected = fields.Boolean(
        compute="_compute_is_selected", string="Chosen",
    )

    _amount_positive = models.Constraint(
        "CHECK (total_amount >= 0)",
        "A quotation cannot be a negative amount.",
    )

    @api.depends("form_id.selected_quote_id")
    def _compute_is_selected(self):
        for quote in self:
            quote.is_selected = quote.form_id.selected_quote_id == quote

    @api.depends("partner_id", "total_amount")
    def _compute_display_name(self):
        for quote in self:
            quote.display_name = "%s - %s" % (
                quote.partner_id.display_name or "",
                quote.total_amount,
            )
