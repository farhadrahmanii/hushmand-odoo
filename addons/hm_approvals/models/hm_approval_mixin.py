# Part of hm_approvals. See LICENSE file for full copyright and licensing details.
"""Make any model approvable.

Inherit the mixin and the model gains a submit-approve-reject cycle::

    class PurchaseRequest(models.Model):
        _name = "purchase.request"
        _inherit = ["purchase.request", "hm.approval.mixin"]

        def _on_approval_approved(self, request):
            self.state = "approved"

Nothing else is required. The steps themselves are configured by the customer
at run time, not written in code, which is the point: the same module serves
an office that needs one signature and one that needs five.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HmApprovalMixin(models.AbstractModel):
    _name = "hm.approval.mixin"
    _description = "Approvable Document"

    approval_request_id = fields.Many2one(
        comodel_name="hm.approval.request",
        string="Approval",
        copy=False,
        readonly=True,
    )
    approval_state = fields.Selection(
        selection=[
            ("none", "Not Submitted"),
            ("pending", "Pending Approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        string="Approval Status",
        compute="_compute_approval_state",
        store=True,
        default="none",
    )
    approval_current_step = fields.Char(
        string="Awaiting",
        related="approval_request_id.current_step_name",
        readonly=True,
    )
    approval_can_act = fields.Boolean(
        string="You Can Approve",
        compute="_compute_approval_can_act",
        help="Whether the current user is an approver for the current step.",
    )

    @api.depends("approval_request_id.state")
    def _compute_approval_state(self):
        for record in self:
            record.approval_state = (
                record.approval_request_id.state
                if record.approval_request_id
                else "none"
            )

    @api.depends_context("uid")
    def _compute_approval_can_act(self):
        # Without depends_context the value computed for the first user is
        # cached and served to the next one, which would show an Approve
        # button to somebody who cannot approve.
        for record in self:
            request = record.approval_request_id
            line = request.current_line_id if request else False
            record.approval_can_act = bool(
                request
                and request.state == "pending"
                and line
                and self.env.user in line.approver_ids
            )

    # ------------------------------------------------------------------
    # Public actions
    # ------------------------------------------------------------------

    def action_submit_for_approval(self):
        """Start the approval chain for these documents."""
        Process = self.env["hm.approval.process"]
        for record in self:
            if record.approval_state == "pending":
                raise UserError(
                    _("%s is already awaiting approval.") % record.display_name
                )
            process = Process._process_for(record)
            if not process:
                raise UserError(
                    _("No approval process is configured for %s.")
                    % record._description
                )
            request = self.env["hm.approval.request"]._start(record, process)
            record.approval_request_id = request
        return True

    def action_approve(self):
        for record in self:
            record._require_request().approve()
        return True

    def action_reject(self):
        """Open the rejection wizard, since a reason is usually required."""
        self.ensure_one()
        self._require_request()
        return {
            "type": "ir.actions.act_window",
            "name": _("Reject"),
            "res_model": "hm.approval.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_request_id": self.approval_request_id.id,
            },
        }

    def action_cancel_approval(self):
        for record in self:
            record._require_request().action_cancel()
        return True

    def action_view_approval(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "hm.approval.request",
            "res_id": self.approval_request_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def _require_request(self):
        self.ensure_one()
        if not self.approval_request_id:
            raise UserError(
                _("%s has not been submitted for approval.") % self.display_name
            )
        return self.approval_request_id

    # ------------------------------------------------------------------
    # Hooks, for the inheriting model to override
    # ------------------------------------------------------------------

    def _on_approval_approved(self, request):
        """Called once every step has approved. Override to act on it."""

    def _on_approval_rejected(self, request):
        """Called when any step rejects. Override to act on it."""
