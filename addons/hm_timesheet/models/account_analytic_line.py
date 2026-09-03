# Part of hm_timesheet. See LICENSE file for full copyright and licensing details.
"""Timesheet entries, and the lock a submitted week puts on them.

Entries stay ordinary ``account.analytic.line`` records. This adds two things
to them: the sheet they belong to, found from the employee and the date, and
a refusal to change once that sheet has been submitted.

The refusal is the point of the module. A week somebody has approved is a
statement about hours worked, and an approved statement that can still be
edited underneath the approver is not an approval at all.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError

#: Fields the machinery itself sets. Writing only these is not a change to
#: what the employee recorded, so a locked sheet does not refuse them.
STRUCTURAL_FIELDS = {"sheet_id"}


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    sheet_id = fields.Many2one(
        comodel_name="hm.timesheet.sheet",
        string="Timesheet",
        index=True,
        ondelete="set null",
        copy=False,
    )
    sheet_state = fields.Selection(
        related="sheet_id.state", string="Timesheet Status", store=True,
    )

    # ------------------------------------------------------------------
    # Attachment
    # ------------------------------------------------------------------

    def _is_timesheet_entry(self):
        """Analytic lines are used for more than timesheets.

        A line only belongs on a timesheet when it says who worked and on
        what. Everything else -- a cost allocation, a revenue split -- is an
        analytic line that has nothing to do with anybody's week.
        """
        self.ensure_one()
        return bool(self.employee_id and self.project_id and self.date)

    def _attach_to_sheet(self):
        sheets = self.env["hm.timesheet.sheet"]
        for line in self:
            if line.sheet_id or not line._is_timesheet_entry():
                continue
            sheet = sheets._find_or_create(line.employee_id, line.date)
            if sheet:
                # sudo: an employee logging their own time must be able to
                # open their own week without write access to the model that
                # their manager approves.
                line.sudo().sheet_id = sheet.id

    # ------------------------------------------------------------------
    # The lock
    # ------------------------------------------------------------------

    def _check_sheet_open(self, action):
        locked = self.filtered(
            lambda line: line.sheet_id and line.sheet_id.state in
            ("submitted", "approved")
        )
        if not locked:
            return
        sheet = locked[0].sheet_id
        raise UserError(
            _("%(week)s has been %(state)s, so its entries can no longer be "
              "%(action)s.\n\nReopen the timesheet first, or ask whoever "
              "approved it to.") % {
                "week": sheet.display_name,
                "state": _("submitted") if sheet.state == "submitted"
                         else _("approved"),
                "action": action,
            }
        )

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._attach_to_sheet()
        # Checked after creation, not before: the sheet a new entry belongs to
        # is only known once the entry exists to be asked about.
        lines._check_sheet_open(_("added to"))
        return lines

    def write(self, vals):
        if not STRUCTURAL_FIELDS.issuperset(vals):
            self._check_sheet_open(_("changed"))
        result = super().write(vals)
        if {"employee_id", "date"} & set(vals):
            # The entry may have moved into a different week, or onto someone
            # else's. Left alone it would keep counting towards a sheet it no
            # longer belongs to, and the totals on both weeks would be wrong.
            self._rehome()
        return result

    def _rehome(self):
        """Detach any entry its sheet no longer covers, and re-attach it."""
        strayed = self.filtered(
            lambda line: line.sheet_id and not (
                line.sheet_id.employee_id == line.employee_id
                and line.date
                and line.sheet_id.date_start <= line.date <= line.sheet_id.date_end
            )
        )
        if strayed:
            strayed.sudo().write({"sheet_id": False})
        self.filtered(lambda line: not line.sheet_id)._attach_to_sheet()

    def unlink(self):
        self._check_sheet_open(_("deleted"))
        return super().unlink()
