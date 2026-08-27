# Part of af_hr. See LICENSE file for full copyright and licensing details.
"""Disciplinary actions.

Odoo has no equivalent, in either edition. Organisations that need one
currently keep it in a spreadsheet or a note on the employee, which is exactly
the kind of record that has to be defensible later.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AfEmployeeDiscipline(models.Model):
    _name = "af.employee.discipline"
    _description = "Disciplinary Action"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Employee",
        required=True,
        index=True,
        ondelete="restrict",
        tracking=True,
    )
    department_id = fields.Many2one(
        related="employee_id.department_id",
        string="Department",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        related="employee_id.company_id", store=True, readonly=True,
    )
    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    action_type = fields.Selection(
        selection=[
            ("verbal", "Verbal Warning"),
            ("written", "Written Warning"),
            ("final", "Final Warning"),
            ("suspension", "Suspension"),
            ("termination", "Termination"),
        ],
        string="Action",
        required=True,
        default="verbal",
        tracking=True,
    )
    reason = fields.Char(string="Reason", required=True, tracking=True)
    description = fields.Text(string="Details")
    issued_by_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Issued By",
        tracking=True,
    )
    suspension_date_from = fields.Date(string="Suspended From")
    suspension_date_to = fields.Date(string="Suspended To")
    follow_up_date = fields.Date(
        string="Review On",
        help="When this should be revisited, for example the end of a "
             "probationary warning period.",
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("issued", "Issued"),
            ("acknowledged", "Acknowledged"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )
    acknowledged_date = fields.Date(string="Acknowledged On", readonly=True)

    _suspension_dates = models.Constraint(
        "CHECK (suspension_date_to IS NULL OR suspension_date_from IS NULL "
        "OR suspension_date_from <= suspension_date_to)",
        "A suspension cannot end before it starts.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "af.employee.discipline"
                ) or _("New")
        return super().create(vals_list)

    @api.constrains("action_type", "suspension_date_from", "suspension_date_to")
    def _check_suspension_dates(self):
        for record in self:
            if record.action_type == "suspension" and not record.suspension_date_from:
                raise UserError(
                    _("A suspension needs a start date.")
                )

    def action_issue(self):
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only a draft action can be issued."))
            record.state = "issued"

    def action_acknowledge(self):
        """Recorded separately because whether the employee saw it matters."""
        for record in self:
            if record.state != "issued":
                raise UserError(
                    _("Only an issued action can be acknowledged.")
                )
            record.write({
                "state": "acknowledged",
                "acknowledged_date": fields.Date.context_today(record),
            })

    def action_close(self):
        for record in self:
            if record.state not in ("issued", "acknowledged"):
                raise UserError(
                    _("Only an issued or acknowledged action can be closed.")
                )
            record.state = "closed"

    def action_cancel(self):
        for record in self:
            if record.state == "closed":
                raise UserError(
                    _("A closed action cannot be cancelled. Record a new "
                      "action instead, so the history stays intact.")
                )
            record.state = "cancelled"

    def action_reset_draft(self):
        for record in self:
            if record.state != "cancelled":
                raise UserError(_("Only a cancelled action can be reset."))
            record.state = "draft"
