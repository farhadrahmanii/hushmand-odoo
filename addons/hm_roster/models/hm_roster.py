# Part of hm_roster. See LICENSE file for full copyright and licensing details.
"""Shift rosters.

Odoo Planning is Enterprise, so a Community user scheduling guards, drivers or
a reception desk has nothing. The common fallback is a spreadsheet per month,
where the failure is always the same: somebody ends up on two shifts at once,
or a night nobody is covering goes unnoticed until it is that night.

Both of those are what this checks. A roster that cannot tell you it is
broken is barely better than the spreadsheet.
"""

from datetime import datetime, time, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


def _float_to_time(value):
    """Turn 18.5 into 18:30."""
    hours = int(value) % 24
    minutes = int(round((value - int(value)) * 60))
    if minutes == 60:
        hours, minutes = (hours + 1) % 24, 0
    return time(hours, minutes)


class HmShiftTemplate(models.Model):
    _name = "hm.shift.template"
    _description = "Shift Template"
    _order = "sequence, hour_from"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    hour_from = fields.Float(string="Starts", required=True, default=8.0)
    hour_to = fields.Float(string="Ends", required=True, default=16.0)
    crosses_midnight = fields.Boolean(
        string="Ends Next Day",
        compute="_compute_crosses_midnight",
        store=True,
        help="A night shift beginning at 18:00 and ending at 06:00 finishes "
             "on the following day.",
    )
    duration_hours = fields.Float(
        string="Hours", compute="_compute_duration", store=True,
    )
    color = fields.Integer(string="Colour")
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )

    _hours_in_range = models.Constraint(
        "CHECK (hour_from >= 0 AND hour_from < 24 AND hour_to >= 0 AND hour_to < 24)",
        "Shift hours must be between 0 and 24.",
    )

    @api.depends("hour_from", "hour_to")
    def _compute_crosses_midnight(self):
        for template in self:
            template.crosses_midnight = template.hour_to <= template.hour_from

    @api.depends("hour_from", "hour_to", "crosses_midnight")
    def _compute_duration(self):
        for template in self:
            span = template.hour_to - template.hour_from
            template.duration_hours = span + 24 if span <= 0 else span

    @api.depends("name", "hour_from", "hour_to")
    def _compute_display_name(self):
        for template in self:
            template.display_name = "%s (%02d:%02d - %02d:%02d)" % (
                template.name or "",
                int(template.hour_from), int((template.hour_from % 1) * 60),
                int(template.hour_to), int((template.hour_to % 1) * 60),
            )


class HmRoster(models.Model):
    _name = "hm.roster"
    _description = "Roster"
    _inherit = ["mail.thread", "hm.license.gate"]
    _licence_module = "hm_roster"
    _order = "date_from desc, id desc"

    name = fields.Char(required=True, tracking=True)
    date_from = fields.Date(string="From", required=True, tracking=True)
    date_to = fields.Date(string="To", required=True, tracking=True)
    location = fields.Char(
        string="Location",
        help="Gate, building or site this roster covers.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("published", "Published"),
            ("closed", "Closed"),
        ],
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )
    shift_ids = fields.One2many(
        comodel_name="hm.roster.shift",
        inverse_name="roster_id",
        string="Shifts",
    )
    shift_count = fields.Integer(compute="_compute_counts")
    unassigned_count = fields.Integer(
        compute="_compute_counts",
        help="Shifts with nobody on them.",
    )
    notes = fields.Text()

    _dates_in_order = models.Constraint(
        "CHECK (date_from <= date_to)",
        "A roster cannot end before it starts.",
    )

    @api.depends("shift_ids", "shift_ids.employee_id")
    def _compute_counts(self):
        for roster in self:
            roster.shift_count = len(roster.shift_ids)
            roster.unassigned_count = len(
                roster.shift_ids.filtered(lambda s: not s.employee_id)
            )

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def action_publish(self):
        """Publish, but not over an unfinished roster.

        A roster with unassigned shifts is the exact thing people publish by
        accident and discover on the night. It has to be a deliberate act.
        """
        for roster in self:
            if roster.state != "draft":
                raise UserError(_("Only a draft roster can be published."))
            if not roster.shift_ids:
                raise UserError(
                    _("%s has no shifts.") % roster.name
                )
            if roster.unassigned_count and not self.env.context.get(
                "allow_unassigned"
            ):
                raise UserError(
                    _("%(count)s shift(s) on %(roster)s have nobody assigned. "
                      "Assign them, or publish again from the button that "
                      "confirms you meant to.")
                    % {"count": roster.unassigned_count, "roster": roster.name}
                )
            roster.state = "published"
            roster.shift_ids._notify_assignees()

    def action_publish_with_gaps(self):
        """Publish knowing some shifts are uncovered."""
        return self.with_context(allow_unassigned=True).action_publish()

    def action_close(self):
        for roster in self:
            if roster.state != "published":
                raise UserError(_("Only a published roster can be closed."))
            roster.state = "closed"

    def action_reset_draft(self):
        for roster in self:
            if roster.state == "closed":
                raise UserError(
                    _("A closed roster cannot be reopened. Copy it instead.")
                )
            roster.state = "draft"

    def action_view_shifts(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Shifts"),
            "res_model": "hm.roster.shift",
            "view_mode": "list,form",
            "domain": [("roster_id", "=", self.id)],
            "context": {"default_roster_id": self.id},
        }


class HmRosterShift(models.Model):
    _name = "hm.roster.shift"
    _description = "Roster Shift"
    _order = "date, start_datetime, id"

    roster_id = fields.Many2one(
        comodel_name="hm.roster",
        string="Roster",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        related="roster_id.company_id", store=True, readonly=True,
    )
    state = fields.Selection(
        related="roster_id.state", store=True, readonly=True, index=True,
    )

    date = fields.Date(string="Date", required=True, index=True)
    template_id = fields.Many2one(
        comodel_name="hm.shift.template",
        string="Shift",
        help="Sets the hours. They can still be overridden.",
    )
    hour_from = fields.Float(string="Starts", required=True, default=8.0)
    hour_to = fields.Float(string="Ends", required=True, default=16.0)

    start_datetime = fields.Datetime(
        compute="_compute_window", store=True, index=True,
    )
    end_datetime = fields.Datetime(compute="_compute_window", store=True)
    duration_hours = fields.Float(compute="_compute_window", store=True)

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Assigned To",
        index="btree_not_null",
    )
    location = fields.Char(string="Post")
    notes = fields.Char()

    _hours_in_range = models.Constraint(
        "CHECK (hour_from >= 0 AND hour_from < 24 AND hour_to >= 0 AND hour_to < 24)",
        "Shift hours must be between 0 and 24.",
    )

    # ------------------------------------------------------------------
    # Times
    # ------------------------------------------------------------------

    @api.onchange("template_id")
    def _onchange_template(self):
        for shift in self:
            if shift.template_id:
                shift.hour_from = shift.template_id.hour_from
                shift.hour_to = shift.template_id.hour_to

    @api.depends("date", "hour_from", "hour_to")
    def _compute_window(self):
        """A night shift ends on the following day, which is the whole reason
        these are datetimes rather than a pair of times."""
        for shift in self:
            if not shift.date:
                shift.start_datetime = shift.end_datetime = False
                shift.duration_hours = 0.0
                continue

            start = datetime.combine(shift.date, _float_to_time(shift.hour_from))
            end = datetime.combine(shift.date, _float_to_time(shift.hour_to))
            if end <= start:
                end += timedelta(days=1)

            shift.start_datetime = start
            shift.end_datetime = end
            shift.duration_hours = (end - start).total_seconds() / 3600.0

    # ------------------------------------------------------------------
    # Conflicts
    # ------------------------------------------------------------------

    @api.constrains("employee_id", "start_datetime", "end_datetime")
    def _check_no_double_booking(self):
        """Nobody works two places at once.

        This is the failure a spreadsheet roster always eventually has, and it
        is only ever noticed on the night, so it is refused outright.
        """
        for shift in self:
            if not shift.employee_id or not shift.start_datetime:
                continue
            clash = self.search([
                ("id", "!=", shift.id),
                ("employee_id", "=", shift.employee_id.id),
                ("start_datetime", "<", shift.end_datetime),
                ("end_datetime", ">", shift.start_datetime),
            ], limit=1)
            if clash:
                raise ValidationError(
                    _("%(employee)s is already on a shift from %(start)s to "
                      "%(end)s.")
                    % {
                        "employee": shift.employee_id.name,
                        "start": clash.start_datetime,
                        "end": clash.end_datetime,
                    }
                )

    @api.constrains("date", "roster_id")
    def _check_date_within_roster(self):
        for shift in self:
            roster = shift.roster_id
            if not (roster.date_from <= shift.date <= roster.date_to):
                raise ValidationError(
                    _("%(date)s is outside the roster period "
                      "%(start)s to %(end)s.")
                    % {
                        "date": shift.date,
                        "start": roster.date_from,
                        "end": roster.date_to,
                    }
                )

    # ------------------------------------------------------------------
    # Notification
    # ------------------------------------------------------------------

    def _notify_assignees(self):
        """Tell people what they are working."""
        for shift in self:
            employee = shift.employee_id
            if not employee or not employee.user_id:
                continue
            # sudo: whoever publishes the roster should not need rights over
            # every assignee's records in order to tell them their shift.
            shift.roster_id.sudo().message_post(
                body=_("%(employee)s: %(date)s, %(start)s to %(end)s")
                % {
                    "employee": employee.name,
                    "date": shift.date,
                    "start": shift.start_datetime,
                    "end": shift.end_datetime,
                },
                partner_ids=employee.user_id.partner_id.ids,
            )

    @api.depends("date", "template_id", "employee_id")
    def _compute_display_name(self):
        for shift in self:
            parts = [str(shift.date or "")]
            if shift.template_id:
                parts.append(shift.template_id.name)
            if shift.employee_id:
                parts.append(shift.employee_id.name)
            shift.display_name = " - ".join(p for p in parts if p)
