# Part of af_correspondence. See LICENSE file for full copyright and licensing details.
"""The maktoob register.

Every Afghan office keeps a bound register of official letters: what came in,
what went out, its number, who it was from or to, and who was given it to deal
with. The register is the record of record -- when a ministry asks what
happened to a letter, this is what gets consulted.

Odoo has no concept of it. Attaching a scan to a contact loses the sequence,
which is the part that matters: numbers are issued in order, and a gap in the
outgoing numbers is a question somebody has to answer.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AfCorrespondence(models.Model):
    _name = "af.correspondence"
    _description = "Correspondence"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(
        string="Register No.",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
        tracking=True,
        help="Issued in order by the register. Not editable, because the "
             "sequence is the point.",
    )
    direction = fields.Selection(
        selection=[("incoming", "Incoming"), ("outgoing", "Outgoing")],
        required=True,
        default="incoming",
        tracking=True,
        index=True,
    )
    subject = fields.Char(string="Subject", required=True, tracking=True)
    date = fields.Date(
        string="Register Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        index=True,
    )
    letter_date = fields.Date(
        string="Letter Date",
        tracking=True,
        help="The date written on the letter itself, which is often not the "
             "day it arrived.",
    )
    letter_reference = fields.Char(
        string="Their Reference",
        tracking=True,
        help="The number the other office put on it.",
    )

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Correspondent",
        tracking=True,
        index="btree_not_null",
        help="The ministry, office or person at the other end.",
    )
    correspondent_name = fields.Char(
        string="From / To",
        tracking=True,
        help="Used when the correspondent is not a contact in the system, "
             "which for a one-off letter from a district office is normal.",
    )

    assigned_to_id = fields.Many2one(
        comodel_name="res.users",
        string="Assigned To",
        tracking=True,
        help="Who has to act on it. An incoming letter nobody owns is a "
             "letter nobody answers.",
    )
    due_date = fields.Date(string="Reply By", tracking=True)

    state = fields.Selection(
        selection=[
            ("registered", "Registered"),
            ("in_progress", "In Progress"),
            ("answered", "Answered"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        default="registered",
        required=True,
        tracking=True,
        index=True,
    )

    reply_to_id = fields.Many2one(
        comodel_name="af.correspondence",
        string="In Reply To",
        index="btree_not_null",
        help="The incoming letter this one answers.",
        domain="[('direction', '=', 'incoming'), ('id', '!=', id)]",
    )
    reply_ids = fields.One2many(
        comodel_name="af.correspondence",
        inverse_name="reply_to_id",
        string="Replies",
    )
    reply_count = fields.Integer(compute="_compute_reply_count")

    department = fields.Char(string="Department")
    notes = fields.Text()
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    attachment_count = fields.Integer(compute="_compute_attachment_count")

    _register_no_uniq = models.Constraint(
        "unique(name, company_id)",
        "That register number has already been used.",
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------

    def _compute_reply_count(self):
        counts = dict(self._read_group(
            [("reply_to_id", "in", self.ids)],
            groupby=["reply_to_id"], aggregates=["__count"],
        ))
        for record in self:
            record.reply_count = counts.get(record, 0)

    def _compute_attachment_count(self):
        counts = dict(self.env["ir.attachment"]._read_group(
            [("res_model", "=", self._name), ("res_id", "in", self.ids)],
            groupby=["res_id"], aggregates=["__count"],
        ))
        for record in self:
            record.attachment_count = counts.get(record.id, 0)

    @api.depends("name", "subject")
    def _compute_display_name(self):
        for record in self:
            record.display_name = " - ".join(
                p for p in (record.name, record.subject) if p and p != _("New")
            ) or _("New")

    # ------------------------------------------------------------------
    # Numbering
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        """Incoming and outgoing letters are numbered in separate series.

        That is how a paper register works: the outgoing book and the incoming
        book each start at one, and a gap in either is a question.
        """
        for vals in vals_list:
            if vals.get("name", _("New")) != _("New"):
                continue
            direction = vals.get("direction", "incoming")
            code = "af.correspondence.%s" % direction
            company_id = vals.get("company_id") or self.env.company.id
            vals["name"] = self.env["ir.sequence"].with_company(
                company_id
            ).next_by_code(code) or _("New")
        return super().create(vals_list)

    def write(self, vals):
        if "direction" in vals:
            changing = self.filtered(lambda r: r.direction != vals["direction"])
            if changing:
                raise UserError(
                    _("The direction cannot be changed once a letter is "
                      "registered — its number comes from that series. "
                      "Cancel it and register a new one.")
                )
        return super().write(vals)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_start(self):
        for record in self:
            if record.state != "registered":
                raise UserError(_("Only a registered letter can be started."))
            record.state = "in_progress"

    def action_mark_answered(self):
        for record in self:
            if record.state not in ("registered", "in_progress"):
                raise UserError(_("This letter is already finished."))
            record.state = "answered"

    def action_close(self):
        for record in self:
            if record.state == "cancelled":
                raise UserError(_("A cancelled letter cannot be closed."))
            record.state = "closed"

    def action_cancel(self):
        for record in self:
            if record.state == "closed":
                raise UserError(
                    _("A closed letter cannot be cancelled. The register is a "
                      "record of what happened.")
                )
            record.state = "cancelled"

    def action_reset(self):
        for record in self:
            record.state = "registered"

    def action_draft_reply(self):
        """Open an outgoing letter answering this one."""
        self.ensure_one()
        if self.direction != "incoming":
            raise UserError(
                _("Only an incoming letter is replied to.")
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("Reply"),
            "res_model": "af.correspondence",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_direction": "outgoing",
                "default_reply_to_id": self.id,
                "default_partner_id": self.partner_id.id,
                "default_correspondent_name": self.correspondent_name,
                "default_subject": _("Re: %s") % self.subject,
                "default_assigned_to_id": self.assigned_to_id.id,
            },
        }

    def action_view_replies(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Replies"),
            "res_model": "af.correspondence",
            "view_mode": "list,form",
            "domain": [("reply_to_id", "=", self.id)],
        }
