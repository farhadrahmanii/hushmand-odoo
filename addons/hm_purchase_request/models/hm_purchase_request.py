# Part of hm_purchase_request. See LICENSE file for full copyright and licensing details.
"""Purchase requests.

Odoo starts at the RFQ: someone has already decided what to buy and from whom.
Most organisations have a step before that, where a department asks for
something and the request is checked and approved on its own merits before
anyone talks to a supplier. Community has nothing for it.

This is that step. It is also the first consumer of ``hm.approval.mixin``, so
who approves a request, in what order, and under what conditions is
configuration rather than code.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HmPurchaseRequest(models.Model):
    _name = "hm.purchase.request"
    _description = "Purchase Request"
    _inherit = ["hm.approval.mixin", "mail.thread", "mail.activity.mixin"]
    _order = "date_request desc, id desc"

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    requester_id = fields.Many2one(
        comodel_name="res.users",
        string="Requested By",
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
    )
    date_request = fields.Date(
        string="Request Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    date_required = fields.Date(
        string="Needed By",
        tracking=True,
        help="When the goods or services are actually needed.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id", readonly=True,
    )
    vendor_id = fields.Many2one(
        comodel_name="res.partner",
        string="Suggested Vendor",
        domain="[('is_company', '=', True)]",
        help="Optional. A suggestion from the requester, not a commitment.",
    )
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Budget Line",
        tracking=True,
        help="The budget this request is to be charged against.",
    )
    reason = fields.Text(
        string="Justification",
        help="Why this is needed. Approvers read this first.",
    )

    line_ids = fields.One2many(
        comodel_name="hm.purchase.request.line",
        inverse_name="request_id",
        string="Items",
        copy=True,
    )
    amount_total = fields.Monetary(
        string="Estimated Total",
        compute="_compute_amount_total",
        store=True,
        tracking=True,
        help="An estimate from the requester. The real figure comes from the "
             "quotation.",
    )

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("to_approve", "Waiting Approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("purchased", "Ordered"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )

    purchase_order_ids = fields.One2many(
        comodel_name="purchase.order",
        inverse_name="hm_request_id",
        string="Purchase Orders",
        readonly=True,
    )
    purchase_order_count = fields.Integer(
        compute="_compute_purchase_order_count", string="Orders",
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------

    @api.depends("line_ids.price_subtotal")
    def _compute_amount_total(self):
        for request in self:
            request.amount_total = sum(request.line_ids.mapped("price_subtotal"))

    def _compute_purchase_order_count(self):
        counts = dict(
            self.env["purchase.order"]._read_group(
                [("hm_request_id", "in", self.ids)],
                groupby=["hm_request_id"],
                aggregates=["__count"],
            )
        )
        for request in self:
            request.purchase_order_count = counts.get(request, 0)

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                company_id = vals.get("company_id") or self.env.company.id
                vals["name"] = self.env["ir.sequence"].with_company(
                    company_id
                ).next_by_code("hm.purchase.request") or _("New")
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------

    def action_submit(self):
        """Send the request for approval."""
        for request in self:
            if request.state != "draft":
                raise UserError(
                    _("%s has already been submitted.") % request.name
                )
            if not request.line_ids:
                raise UserError(
                    _("Add at least one item to %s before submitting it.")
                    % request.name
                )
            request.action_submit_for_approval()
            request.state = "to_approve"
        return True

    def action_cancel(self):
        for request in self:
            if request.state in ("purchased", "cancelled"):
                raise UserError(
                    _("%s cannot be cancelled.") % request.name
                )
            if request.approval_state == "pending":
                request.action_cancel_approval()
            request.state = "cancelled"

    def action_reset_draft(self):
        for request in self:
            if request.state not in ("rejected", "cancelled"):
                raise UserError(
                    _("Only a rejected or cancelled request can be reopened.")
                )
            request.write({"state": "draft", "approval_request_id": False})

    # ------------------------------------------------------------------
    # Approval hooks
    # ------------------------------------------------------------------

    def _on_approval_approved(self, request):
        """Called by the approval engine once every step has approved."""
        self.write({"state": "approved"})
        self.message_post(body=_("Approved. This request can now be ordered."))

    def _on_approval_rejected(self, request):
        self.write({"state": "rejected"})

    # ------------------------------------------------------------------
    # Turning it into a purchase
    # ------------------------------------------------------------------

    def action_create_rfq(self):
        """Create a request for quotation from an approved request."""
        self.ensure_one()
        if self.state != "approved":
            raise UserError(
                _("%s has to be approved before it can be ordered.") % self.name
            )
        if not self.vendor_id:
            raise UserError(
                _("Set a vendor on %s before creating a quotation.") % self.name
            )

        order = self.env["purchase.order"].create({
            "partner_id": self.vendor_id.id,
            "company_id": self.company_id.id,
            "origin": self.name,
            "hm_request_id": self.id,
            "order_line": [
                (0, 0, line._prepare_purchase_order_line())
                for line in self.line_ids
            ],
        })
        self.state = "purchased"
        self.message_post(
            body=_("Quotation %s created.") % order.display_name
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "purchase.order",
            "res_id": order.id,
            "view_mode": "form",
        }

    def action_view_purchase_orders(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Purchase Orders"),
            "res_model": "purchase.order",
            "view_mode": "list,form",
            "domain": [("hm_request_id", "=", self.id)],
        }


class HmPurchaseRequestLine(models.Model):
    _name = "hm.purchase.request.line"
    _description = "Purchase Request Item"
    _order = "request_id, sequence, id"

    request_id = fields.Many2one(
        comodel_name="hm.purchase.request",
        string="Request",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        domain=[("purchase_ok", "=", True)],
        help="Optional. A request can describe something that is not yet a "
             "product in the catalogue.",
    )
    name = fields.Char(
        string="Description",
        required=True,
        help="What is being requested, in the requester's own words.",
    )
    product_qty = fields.Float(
        string="Quantity", digits="Product Unit", required=True, default=1.0,
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom", string="Unit",
    )
    price_unit = fields.Float(
        string="Estimated Price", digits="Product Price",
    )
    price_subtotal = fields.Monetary(
        string="Subtotal", compute="_compute_price_subtotal", store=True,
    )
    currency_id = fields.Many2one(
        related="request_id.currency_id", readonly=True,
    )
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Budget Line",
        help="Overrides the budget line set on the request.",
    )
    notes = fields.Char(string="Notes")

    _qty_positive = models.Constraint(
        "CHECK (product_qty > 0)",
        "A requested quantity must be greater than zero.",
    )

    @api.depends("product_qty", "price_unit")
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.product_qty * line.price_unit

    @api.onchange("product_id")
    def _onchange_product(self):
        for line in self:
            if not line.product_id:
                continue
            if not line.name:
                line.name = line.product_id.display_name
            line.product_uom_id = line.product_id.uom_po_id or line.product_id.uom_id
            if not line.price_unit:
                line.price_unit = line.product_id.standard_price

    def _prepare_purchase_order_line(self):
        """Values for the purchase.order.line this item becomes.

        Note product_uom_id: Odoo 19 renamed it from product_uom, and the
        analytic field is a distribution rather than a plain link.
        """
        self.ensure_one()
        values = {
            "name": self.name,
            "product_qty": self.product_qty,
            "price_unit": self.price_unit,
        }
        if self.product_id:
            values["product_id"] = self.product_id.id
        if self.product_uom_id:
            values["product_uom_id"] = self.product_uom_id.id

        analytic = self.analytic_account_id or self.request_id.analytic_account_id
        if analytic:
            values["analytic_distribution"] = {str(analytic.id): 100.0}
        return values
