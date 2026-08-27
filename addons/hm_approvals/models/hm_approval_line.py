# Part of hm_approvals. See LICENSE file for full copyright and licensing details.
"""One step of a running approval."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HmApprovalLine(models.Model):
    _name = "hm.approval.line"
    _description = "Approval Step Instance"
    _order = "request_id, sequence, id"

    request_id = fields.Many2one(
        comodel_name="hm.approval.request",
        string="Request",
        required=True,
        ondelete="cascade",
        index=True,
    )
    step_id = fields.Many2one(
        comodel_name="hm.approval.step",
        string="Step",
        required=True,
        ondelete="restrict",
    )
    name = fields.Char(related="step_id.name", string="Step Name", readonly=True)
    sequence = fields.Integer(default=10, index=True)
    approver_ids = fields.Many2many(
        comodel_name="res.users",
        string="Can Approve",
        help="Anyone here may act on this step. The first to do so decides it.",
    )
    state = fields.Selection(
        selection=[
            ("pending", "Waiting"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        default="pending",
        required=True,
        index=True,
    )
    acted_by_id = fields.Many2one(
        comodel_name="res.users", string="Decided By", readonly=True,
    )
    acted_on = fields.Datetime(string="Decided On", readonly=True)
    comment = fields.Text(string="Comment")

    # ------------------------------------------------------------------
    # Deciding
    # ------------------------------------------------------------------

    def _approve(self, comment=None):
        self.ensure_one()
        if self.state != "pending":
            raise UserError(_("This step has already been decided."))
        if self.step_id.require_comment and not comment:
            raise UserError(
                _("%s requires a comment.") % self.step_id.name
            )

        self._decide("approved", comment)
        self.request_id._activate_next()

    def _reject(self, reason=None):
        self.ensure_one()
        if self.state != "pending":
            raise UserError(_("This step has already been decided."))
        if not self.step_id.allow_reject:
            raise UserError(
                _("%s cannot be rejected.") % self.step_id.name
            )
        if self.step_id.require_comment_on_reject and not reason:
            raise UserError(
                _("A reason is required to reject %s.") % self.step_id.name
            )

        self._decide("rejected", reason)

        # A rejection stops the whole chain. Later steps are cancelled rather
        # than left waiting, so nothing shows as outstanding afterwards.
        later = self.request_id.line_ids.filtered(
            lambda line: line.state == "pending" and line.id != self.id
        )
        later._clear_activities()
        later.write({"state": "cancelled"})

        self.request_id._finish("rejected")

    def _decide(self, state, comment):
        self.ensure_one()
        self._clear_activities()
        self.write({
            "state": state,
            "acted_by_id": self.env.user.id,
            "acted_on": fields.Datetime.now(),
            "comment": comment or self.comment,
        })
        self._post_to_document(state, comment)

    def _post_to_document(self, state, comment):
        """Leave a trace on the document, where people actually look."""
        self.ensure_one()
        record = self.request_id._record()
        if not record or not hasattr(record, "message_post"):
            return

        if state == "approved":
            body = _("%(step)s approved by %(user)s.") % {
                "step": self.step_id.name,
                "user": self.env.user.display_name,
            }
        else:
            body = _("%(step)s rejected by %(user)s.") % {
                "step": self.step_id.name,
                "user": self.env.user.display_name,
            }
        if comment:
            body += "<br/>%s" % comment
        record.message_post(body=body)

    # ------------------------------------------------------------------
    # Activities
    # ------------------------------------------------------------------

    def _notify_approvers(self):
        """Put the document in each approver's Odoo inbox.

        Scheduling one activity per approver means a step assigned to a group
        appears for everyone in it. Whoever acts first decides the step, and
        the rest are withdrawn.
        """
        for line in self:
            record = line.request_id._record()
            if not record or not hasattr(record, "activity_schedule"):
                continue
            for approver in line.approver_ids:
                record.activity_schedule(
                    user_id=approver.id,
                    summary=_("Approval: %s") % line.step_id.name,
                    note=_("%(document)s is waiting for your approval.")
                    % {"document": record.display_name},
                )

    def _clear_activities(self):
        """Withdraw outstanding activities for these steps."""
        for line in self:
            record = line.request_id._record()
            if not record:
                continue
            summary = _("Approval: %s") % line.step_id.name
            activities = self.env["mail.activity"].sudo().search([
                ("res_model", "=", line.request_id.res_model),
                ("res_id", "=", line.request_id.res_id),
                ("summary", "=", summary),
            ])
            activities.unlink()

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    @api.depends("step_id.name", "state")
    def _compute_display_name(self):
        for line in self:
            line.display_name = line.step_id.name or ""
