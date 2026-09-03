# Part of hm_timesheet. See LICENSE file for full copyright and licensing details.
"""Weekly timesheets.

Odoo Community records time on tasks perfectly well -- ``hr_timesheet`` gives
every employee an analytic line per entry, and the pivot and list views to
read them back. What it has no concept of is a **week that gets submitted**:
there is nothing to approve, nothing to lock, and nothing to print and sign.
That is Enterprise's ``timesheet_grid``.

This module adds the missing layer, and deliberately adds only that. Entries
stay ordinary ``account.analytic.line`` records, so every report, filter and
export that already reads timesheets keeps working. A sheet is a window onto
the lines that fall inside it, not a second place to store them.

The week runs Saturday to Friday by default, because that is the Afghan
working week, and is configurable per company for everywhere else.
"""

from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import format_date


class HmTimesheetSheet(models.Model):
    _name = "hm.timesheet.sheet"
    _description = "Timesheet"
    _inherit = [
        "hm.approval.mixin", "mail.thread", "mail.activity.mixin",
        "hm.license.gate",
    ]
    _licence_module = "hm_timesheet"
    _order = "date_start desc, id desc"

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Employee",
        required=True,
        tracking=True,
        default=lambda self: self.env.user.employee_id,
    )
    user_id = fields.Many2one(
        related="employee_id.user_id", store=True, string="User",
    )
    department_id = fields.Many2one(
        related="employee_id.department_id", store=True, string="Department",
    )
    manager_id = fields.Many2one(
        related="employee_id.parent_id", store=True, string="Manager",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )

    date_start = fields.Date(
        string="Week Beginning",
        required=True,
        tracking=True,
        default=lambda self: self._week_start(fields.Date.context_today(self)),
        help="Snapped to the first day of the week when saved.",
    )
    date_end = fields.Date(
        string="Week Ending", compute="_compute_date_end", store=True,
    )

    line_ids = fields.One2many(
        comodel_name="account.analytic.line",
        inverse_name="sheet_id",
        string="Entries",
    )
    total_hours = fields.Float(
        string="Hours", compute="_compute_hours", store=True,
    )
    # Stored, both of them. A search-view filter on a non-stored computed
    # field does not merely fail: it refuses the whole registry load with
    # "Unsearchable field in domain", and every module in the database stops
    # installing. "Short of Expected" is a filter, so these have to be real
    # columns.
    expected_hours = fields.Float(
        string="Expected", compute="_compute_expected_hours", store=True,
        help="What the employee's working calendar asks for in a full week.",
    )
    difference_hours = fields.Float(
        string="Difference", compute="_compute_expected_hours", store=True,
        help="Recorded minus expected. Negative means the week is short.",
    )

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="draft",
        required=True,
        readonly=True,
        tracking=True,
        index=True,
    )

    _one_sheet_per_week = models.Constraint(
        "unique(employee_id, date_start, company_id)",
        "That employee already has a timesheet for this week.",
    )

    # ------------------------------------------------------------------
    # The week
    # ------------------------------------------------------------------

    @api.model
    def _week_start(self, day, company=None):
        """The first day of the week `day` falls in, for this company.

        Odoo writes weekdays the ISO way, 1 for Monday through 7 for Sunday,
        and Python counts them from 0. Converting in one place keeps the
        off-by-one where it can be seen.
        """
        company = company or self.env.company
        first = int(company.hm_timesheet_week_start or "6")
        return day - timedelta(days=(day.weekday() - (first - 1)) % 7)

    @api.depends("date_start")
    def _compute_date_end(self):
        for sheet in self:
            sheet.date_end = (
                sheet.date_start + timedelta(days=6) if sheet.date_start else False
            )

    @api.depends("employee_id", "date_start", "date_end")
    def _compute_display_name(self):
        for sheet in self:
            if not sheet.date_start:
                sheet.display_name = _("Timesheet")
                continue
            sheet.display_name = "%s: %s - %s" % (
                sheet.employee_id.name or _("Timesheet"),
                format_date(self.env, sheet.date_start),
                format_date(self.env, sheet.date_end),
            )

    # ------------------------------------------------------------------
    # Totals
    # ------------------------------------------------------------------

    @api.depends("line_ids.unit_amount")
    def _compute_hours(self):
        for sheet in self:
            sheet.total_hours = sum(sheet.line_ids.mapped("unit_amount"))

    @api.depends("employee_id", "total_hours")
    def _compute_expected_hours(self):
        """What a full week is, according to the employee's own calendar.

        Summed from the calendar's attendances rather than read off
        ``hours_per_day``, because that field is an average and a week of
        four nine-hour days is not the same as five seven-hour ones.
        """
        for sheet in self:
            calendar = sheet.employee_id.resource_calendar_id
            hours = sum(
                attendance.hour_to - attendance.hour_from
                for attendance in calendar.attendance_ids
            )
            if calendar.two_weeks_calendar:
                # Such a calendar holds two weeks of attendances; a single
                # week is half of what they add up to.
                hours = hours / 2.0
            sheet.expected_hours = hours
            sheet.difference_hours = sheet.total_hours - hours

    # ------------------------------------------------------------------
    # Keeping the window honest
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("date_start"):
                company = self.env["res.company"].browse(
                    vals.get("company_id")
                ) or self.env.company
                vals["date_start"] = self._week_start(
                    fields.Date.to_date(vals["date_start"]), company
                )
        sheets = super().create(vals_list)
        sheets._collect_lines()
        return sheets

    def write(self, vals):
        if vals.get("date_start"):
            vals["date_start"] = self._week_start(
                fields.Date.to_date(vals["date_start"])
            )
        result = super().write(vals)
        if {"date_start", "employee_id"} & set(vals):
            self._collect_lines()
        return result

    def _collect_lines(self):
        """Adopt the entries that fall inside this sheet.

        A sheet is a window, so it shows whatever is already there. Time
        logged before anyone opened a timesheet still belongs to the week it
        was worked in.
        """
        for sheet in self:
            if not (sheet.employee_id and sheet.date_start):
                continue
            orphans = self.env["account.analytic.line"].search([
                ("employee_id", "=", sheet.employee_id.id),
                ("date", ">=", sheet.date_start),
                ("date", "<=", sheet.date_end),
                ("project_id", "!=", False),
                ("sheet_id", "=", False),
            ])
            if orphans:
                orphans.write({"sheet_id": sheet.id})

    @api.model
    def _find_or_create(self, employee, day):
        """The sheet a given day's work belongs to, made if it is not there."""
        if not employee:
            return self.browse()
        company = employee.company_id or self.env.company
        start = self._week_start(day, company)
        sheet = self.search([
            ("employee_id", "=", employee.id),
            ("date_start", "=", start),
            ("company_id", "=", company.id),
        ], limit=1)
        if sheet:
            return sheet
        return self.sudo().create({
            "employee_id": employee.id,
            "date_start": start,
            "company_id": company.id,
        })

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------

    def action_submit(self):
        for sheet in self:
            if sheet.state != "draft":
                raise UserError(
                    _("%s has already been submitted.") % sheet.display_name
                )
            if not sheet.line_ids:
                raise UserError(
                    _("There is no time recorded on %s. An empty week is not "
                      "a timesheet.") % sheet.display_name
                )
            sheet.action_submit_for_approval()
            sheet.state = "submitted"
        return True

    def action_reset_draft(self):
        for sheet in self:
            if sheet.state not in ("rejected", "submitted"):
                raise UserError(
                    _("Only a submitted or rejected timesheet can be reopened. "
                      "%s is approved, and its hours have been signed off.")
                    % sheet.display_name
                )
            if sheet.approval_state == "pending":
                sheet.action_cancel_approval()
            sheet.write({"state": "draft", "approval_request_id": False})

    def _on_approval_approved(self, request):
        self.write({"state": "approved"})
        self.message_post(body=_("Timesheet approved. The entries are now locked."))

    def _on_approval_rejected(self, request):
        self.write({"state": "rejected"})

    @property
    def _locked(self):
        return self.state in ("submitted", "approved")

    # ------------------------------------------------------------------
    # Printing
    # ------------------------------------------------------------------

    def _report_grid(self):
        """The week as a grid: what was worked on down, days across.

        A printed timesheet gets read across a row -- what did this project
        take this week -- and down a column -- what did Tuesday look like. A
        flat list of entries answers neither without the reader adding up.
        """
        self.ensure_one()
        days = [self.date_start + timedelta(days=offset) for offset in range(7)]

        rows = {}
        for line in self.line_ids:
            key = (line.project_id.id, line.task_id.id)
            row = rows.setdefault(key, {
                "project": line.project_id.display_name or _("No project"),
                "task": line.task_id.name or "",
                "hours": dict.fromkeys(days, 0.0),
                "total": 0.0,
            })
            if line.date in row["hours"]:
                row["hours"][line.date] += line.unit_amount
                row["total"] += line.unit_amount

        return {
            "days": days,
            "rows": sorted(rows.values(), key=lambda row: (row["project"], row["task"])),
            "day_totals": {
                day: sum(r["hours"][day] for r in rows.values()) for day in days
            },
            "total": sum(r["total"] for r in rows.values()),
        }


    def action_open_entries(self):
        """The week's entries, in Odoo's own timesheet views."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Entries"),
            "res_model": "account.analytic.line",
            "view_mode": "list,pivot,form",
            "domain": [("sheet_id", "=", self.id)],
            "context": {
                "default_sheet_id": self.id,
                "default_employee_id": self.employee_id.id,
                "search_default_groupby_project": 1,
            },
        }

