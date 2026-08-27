# Part of hm_approvals. See LICENSE file for full copyright and licensing details.
"""A running approval on a document."""

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class HmApprovalRequest(models.Model):
    _name = "hm.approval.request"
    _description = "Approval Request"
    _inherit = ["mail.thread"]
    _order = "create_date desc, id desc"
    _rec_name = "display_name"

    process_id = fields.Many2one(
        comodel_name="hm.approval.process",
        string="Process",
        required=True,
        ondelete="restrict",
        index=True,
    )
    res_model = fields.Char(string="Document Model", required=True, index=True)
    res_id = fields.Integer(string="Document ID", required=True, index=True)
    reference = fields.Char(
        string="Document",
        compute="_compute_reference",
        help="The document under approval, as it names itself.",
    )
    requested_by_id = fields.Many2one(
        comodel_name="res.users",
        string="Requested By",
        default=lambda self: self.env.user,
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
    state = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        default="pending",
        required=True,
        index=True,
        tracking=True,
    )
    line_ids = fields.One2many(
        comodel_name="hm.approval.line",
        inverse_name="request_id",
        string="Steps",
    )
    current_line_id = fields.Many2one(
        comodel_name="hm.approval.line",
        string="Awaiting",
        compute="_compute_current_line",
        store=True,
    )
    current_step_name = fields.Char(
        related="current_line_id.step_id.name", string="Current Step",
    )
    date_done = fields.Datetime(string="Completed On", readonly=True)

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------

    @api.depends("res_model", "res_id")
    def _compute_reference(self):
        for request in self:
            record = request._record()
            request.reference = record.display_name if record else ""

    @api.depends("process_id", "reference", "state")
    def _compute_display_name(self):
        for request in self:
            request.display_name = "%s - %s" % (
                request.process_id.name or "",
                request.reference or _("Document"),
            )

    @api.depends("line_ids.state", "line_ids.sequence")
    def _compute_current_line(self):
        for request in self:
            pending = request.line_ids.filtered(lambda l: l.state == "pending")
            request.current_line_id = pending.sorted("sequence")[:1]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _record(self):
        """The document, or an empty recordset if it has gone."""
        self.ensure_one()
        model = self.env.get(self.res_model)
        if model is None or not self.res_id:
            return self.env["hm.approval.request"].browse()
        record = model.browse(self.res_id)
        return record if record.exists() else model.browse()

    def action_open_document(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": self.res_model,
            "res_id": self.res_id,
            "view_mode": "form",
        }

    # ------------------------------------------------------------------
    # Building the chain
    # ------------------------------------------------------------------

    @api.model
    def _start(self, record, process):
        """Create a request and open its first applicable step."""
        request = self.create({
            "process_id": process.id,
            "res_model": record._name,
            "res_id": record.id,
            "company_id": (
                getattr(record, "company_id", False) or self.env.company
            ).id,
        })
        request._build_lines(record)
        if not request.line_ids:
            # Every step was skipped by its condition, so there is nothing to
            # approve. Completing immediately beats leaving it stuck.
            request._finish("approved")
        else:
            request._activate_next()
        return request

    def _build_lines(self, record):
        self.ensure_one()
        Line = self.env["hm.approval.line"]
        for step in self.process_id.step_ids.sorted("sequence"):
            if not step._applies_to(record):
                continue
            approvers = step._resolve_approvers(record)
            Line.create({
                "request_id": self.id,
                "step_id": step.id,
                "sequence": step.sequence,
                "approver_ids": [(6, 0, approvers.ids)],
            })

    def _activate_next(self):
        """Notify whoever is next, or finish."""
        self.ensure_one()
        line = self.current_line_id
        if not line:
            self._finish("approved")
            return
        line._notify_approvers()

    def _finish(self, state):
        self.ensure_one()
        self.write({"state": state, "date_done": fields.Datetime.now()})
        self.line_ids._clear_activities()

        record = self._record()
        if not record:
            return
        if state == "approved" and hasattr(record, "_on_approval_approved"):
            record._on_approval_approved(self)
        elif state == "rejected" and hasattr(record, "_on_approval_rejected"):
            record._on_approval_rejected(self)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def approve(self, comment=None):
        """Approve the current step on behalf of the current user."""
        for request in self:
            line = request._line_for_current_user()
            line._approve(comment)
        return True

    def reject(self, reason=None):
        for request in self:
            line = request._line_for_current_user()
            line._reject(reason)
        return True

    def action_cancel(self):
        for request in self:
            if request.state != "pending":
                raise UserError(
                    _("Only a pending request can be cancelled.")
                )
            request.write({
                "state": "cancelled",
                "date_done": fields.Datetime.now(),
            })
            request.line_ids._clear_activities()
            request.line_ids.filtered(lambda l: l.state == "pending").write(
                {"state": "cancelled"}
            )

    def _line_for_current_user(self):
        self.ensure_one()
        if self.state != "pending":
            raise UserError(
                _("This request is already %s.") % self.state
            )
        line = self.current_line_id
        if not line:
            raise UserError(_("There is nothing awaiting approval."))
        if self.env.user not in line.approver_ids and not self.env.su:
            raise AccessError(
                _("This step is waiting for %s.")
                % ", ".join(line.approver_ids.mapped("name")) or _("someone else")
            )
        return line
