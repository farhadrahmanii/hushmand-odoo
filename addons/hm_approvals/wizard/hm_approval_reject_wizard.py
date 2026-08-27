# Part of hm_approvals. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import UserError


class HmApprovalRejectWizard(models.TransientModel):
    _name = "hm.approval.reject.wizard"
    _description = "Reject an Approval"

    request_id = fields.Many2one(
        comodel_name="hm.approval.request",
        string="Request",
        required=True,
        readonly=True,
    )
    step_name = fields.Char(
        related="request_id.current_step_name", string="Step", readonly=True,
    )
    reason = fields.Text(string="Reason", required=True)

    def action_confirm(self):
        self.ensure_one()
        if not self.reason.strip():
            raise UserError(_("A reason is required."))
        self.request_id.reject(self.reason)
        return {"type": "ir.actions.act_window_close"}
