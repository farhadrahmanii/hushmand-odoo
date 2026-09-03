# Part of hm_timesheet. See LICENSE file for full copyright and licensing details.
"""Tests for weekly timesheets.

The module's whole claim is that a submitted week stops changing. Most of what
is below is that claim, approached from each direction somebody could get
around it.
"""

from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import common, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TimesheetCase(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.hm_timesheet_week_start = "6"  # Saturday

        cls.project = cls.env["project.project"].create({
            "name": "Water Supply",
            "allow_timesheets": True,
        })
        # The shipped approval process resolves the approver through
        # employee_id.parent_id.user_id, so the employee needs a manager who
        # is a user or nothing can be submitted.
        cls.manager_user = cls.env["res.users"].create({
            "name": "Rahima Sadat",
            "login": "timesheet_manager",
        })
        cls.manager = cls.env["hr.employee"].create({
            "name": "Rahima Sadat",
            "user_id": cls.manager_user.id,
        })
        cls.employee = cls.env["hr.employee"].create({
            "name": "Nasir Ahmad", "parent_id": cls.manager.id,
        })
        cls.other_employee = cls.env["hr.employee"].create({
            "name": "Zarmina Popal", "parent_id": cls.manager.id,
        })
        cls.Sheet = cls.env["hm.timesheet.sheet"]
        cls.Line = cls.env["account.analytic.line"]

        # A known Saturday, so the week arithmetic is checked against a date
        # somebody can verify rather than against today.
        cls.saturday = fields.Date.to_date("2026-08-29")

    def _line(self, day=None, hours=4.0, employee=None, project=None):
        return self.Line.create({
            "name": "Work",
            "project_id": (project or self.project).id,
            "employee_id": (employee or self.employee).id,
            "unit_amount": hours,
            "date": day or self.saturday,
        })


class TestTheWeek(TimesheetCase):

    def test_the_week_starts_on_the_configured_day(self):
        """2026-08-29 is a Saturday, so a Saturday week starts on it."""
        self.assertEqual(self.Sheet._week_start(self.saturday), self.saturday)

    def test_a_midweek_date_snaps_back_to_the_week_start(self):
        wednesday = self.saturday + timedelta(days=4)
        self.assertEqual(self.Sheet._week_start(wednesday), self.saturday)

    def test_the_day_before_belongs_to_the_previous_week(self):
        friday = self.saturday - timedelta(days=1)
        self.assertEqual(
            self.Sheet._week_start(friday), self.saturday - timedelta(days=7)
        )

    def test_a_monday_week_is_a_different_week(self):
        """The Afghan default must not be baked in: elsewhere it is Monday."""
        self.company.hm_timesheet_week_start = "1"
        wednesday = self.saturday + timedelta(days=4)  # 2026-09-02
        self.assertEqual(
            self.Sheet._week_start(wednesday),
            fields.Date.to_date("2026-08-31"),
        )

    def test_creating_a_sheet_snaps_its_start_date(self):
        sheet = self.Sheet.create({
            "employee_id": self.employee.id,
            "date_start": self.saturday + timedelta(days=3),
        })
        self.assertEqual(sheet.date_start, self.saturday)
        self.assertEqual(sheet.date_end, self.saturday + timedelta(days=6))


class TestEntriesFindTheirWeek(TimesheetCase):

    def test_logging_time_creates_the_week(self):
        """Nobody should have to open a timesheet before recording work."""
        line = self._line()
        self.assertTrue(line.sheet_id)
        self.assertEqual(line.sheet_id.employee_id, self.employee)
        self.assertEqual(line.sheet_id.date_start, self.saturday)

    def test_a_second_entry_joins_the_same_week(self):
        first = self._line()
        second = self._line(day=self.saturday + timedelta(days=2))
        self.assertEqual(first.sheet_id, second.sheet_id)

    def test_another_employee_gets_their_own_week(self):
        mine = self._line()
        theirs = self._line(employee=self.other_employee)
        self.assertNotEqual(mine.sheet_id, theirs.sheet_id)

    def test_an_analytic_line_that_is_not_a_timesheet_is_left_alone(self):
        """Analytic lines are used for cost and revenue allocation too, and
        those have nothing to do with anybody's week."""
        line = self.Line.create({"name": "Office rent", "amount": -500.0})
        self.assertFalse(line.sheet_id)

    def test_a_sheet_adopts_entries_that_predate_it(self):
        """Time logged before anyone opened a timesheet still belongs to the
        week it was worked in."""
        line = self._line()
        # Logging time already made a sheet. Clear both it and the link, so
        # what is tested is a fresh sheet finding an entry that predates it
        # rather than the one that created it.
        line.sheet_id.sudo().unlink()
        self.assertFalse(line.sheet_id)

        sheet = self.Sheet.create({
            "employee_id": self.employee.id,
            "date_start": self.saturday,
        })
        self.assertEqual(line.sheet_id, sheet)

    def test_moving_an_entry_to_another_week_moves_the_entry(self):
        """Left attached to the old sheet it would keep counting towards a
        week it is no longer in, and both weeks' totals would be wrong."""
        line = self._line()
        first_week = line.sheet_id
        line.date = self.saturday + timedelta(days=8)

        self.assertNotEqual(line.sheet_id, first_week)
        self.assertEqual(line.sheet_id.date_start, self.saturday + timedelta(days=7))
        self.assertEqual(first_week.total_hours, 0.0)

    def test_totals_add_up(self):
        self._line(hours=7.5)
        line = self._line(day=self.saturday + timedelta(days=1), hours=8.0)
        self.assertEqual(line.sheet_id.total_hours, 15.5)


class TestTheLock(TimesheetCase):

    def _submitted_sheet(self):
        line = self._line()
        sheet = line.sheet_id
        sheet.action_submit()
        return sheet, line

    def test_a_submitted_week_refuses_a_change(self):
        _sheet, line = self._submitted_sheet()
        with self.assertRaises(UserError):
            line.unit_amount = 9.0

    def test_a_submitted_week_refuses_a_deletion(self):
        _sheet, line = self._submitted_sheet()
        with self.assertRaises(UserError):
            line.unlink()

    def test_a_submitted_week_refuses_a_new_entry(self):
        """The obvious way around the lock: leave the existing entries alone
        and add another one."""
        sheet, _line = self._submitted_sheet()
        with self.assertRaises(UserError):
            self._line(day=self.saturday + timedelta(days=1))

    def test_an_approved_week_refuses_a_change(self):
        _sheet, line = self._submitted_sheet()
        line.sheet_id.write({"state": "approved"})
        with self.assertRaises(UserError):
            line.unit_amount = 9.0

    def test_the_machinery_may_still_write_the_link(self):
        """Locking must not stop the module attaching an entry to its sheet,
        or nothing could ever be collected."""
        sheet, line = self._submitted_sheet()
        line.sudo().write({"sheet_id": sheet.id})

    def test_reopening_unlocks_the_entries(self):
        sheet, line = self._submitted_sheet()
        sheet.action_reset_draft()
        line.unit_amount = 9.0
        self.assertEqual(sheet.total_hours, 9.0)

    def test_a_draft_week_is_editable(self):
        line = self._line()
        line.unit_amount = 6.0
        self.assertEqual(line.sheet_id.total_hours, 6.0)


class TestWorkflow(TimesheetCase):

    def test_an_empty_week_cannot_be_submitted(self):
        """An empty week is not a timesheet, and approving one means nothing."""
        sheet = self.Sheet.create({
            "employee_id": self.employee.id,
            "date_start": self.saturday,
        })
        with self.assertRaises(UserError):
            sheet.action_submit()

    def test_submitting_twice_is_refused(self):
        line = self._line()
        line.sheet_id.action_submit()
        with self.assertRaises(UserError):
            line.sheet_id.action_submit()

    def test_an_approved_week_cannot_be_reopened(self):
        """Reopening an approved week would let the hours change underneath
        the person who signed them off."""
        line = self._line()
        line.sheet_id.action_submit()
        line.sheet_id.write({"state": "approved"})
        with self.assertRaises(UserError):
            line.sheet_id.action_reset_draft()

    def test_rejection_sends_it_back_to_the_employee(self):
        line = self._line()
        sheet = line.sheet_id
        sheet.action_submit()
        sheet._on_approval_rejected(sheet.approval_request_id)
        self.assertEqual(sheet.state, "rejected")
        sheet.action_reset_draft()
        self.assertEqual(sheet.state, "draft")

    def test_approval_locks_and_says_so(self):
        line = self._line()
        sheet = line.sheet_id
        sheet.action_submit()
        sheet._on_approval_approved(sheet.approval_request_id)
        self.assertEqual(sheet.state, "approved")
        with self.assertRaises(UserError):
            line.unit_amount = 1.0


class TestExpectedHours(TimesheetCase):

    def test_expected_hours_come_from_the_employee_calendar(self):
        calendar = self.env["resource.calendar"].create({
            "name": "Four nine-hour days",
            "attendance_ids": [
                (0, 0, {"name": "D%s" % day, "dayofweek": str(day),
                        "hour_from": 8.0, "hour_to": 17.0})
                for day in range(4)
            ],
        })
        self.employee.resource_calendar_id = calendar
        sheet = self.Sheet.create({
            "employee_id": self.employee.id,
            "date_start": self.saturday,
        })
        self.assertEqual(sheet.expected_hours, 36.0)

    def test_a_short_week_shows_a_negative_difference(self):
        calendar = self.env["resource.calendar"].create({
            "name": "One eight-hour day",
            "attendance_ids": [
                (0, 0, {"name": "Mon", "dayofweek": "0",
                        "hour_from": 8.0, "hour_to": 16.0}),
            ],
        })
        self.employee.resource_calendar_id = calendar
        line = self._line(hours=5.0)
        self.assertEqual(line.sheet_id.difference_hours, -3.0)


class TestHousekeeping(TimesheetCase):

    @mute_logger("odoo.sql_db")
    def test_one_sheet_per_employee_per_week(self):
        self.Sheet.create({
            "employee_id": self.employee.id,
            "date_start": self.saturday,
        })
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.Sheet.create({
                    "employee_id": self.employee.id,
                    "date_start": self.saturday,
                })

    def test_the_printed_grid_puts_days_across_and_work_down(self):
        self._line(hours=7.5)
        line = self._line(day=self.saturday + timedelta(days=1), hours=8.0)
        grid = line.sheet_id._report_grid()

        self.assertEqual(len(grid["days"]), 7)
        self.assertEqual(len(grid["rows"]), 1, "one project, so one row")
        self.assertEqual(grid["total"], 15.5)
        self.assertEqual(grid["day_totals"][self.saturday], 7.5)

    def test_the_grid_of_an_empty_week_still_renders(self):
        sheet = self.Sheet.create({
            "employee_id": self.employee.id,
            "date_start": self.saturday,
        })
        grid = sheet._report_grid()
        self.assertEqual(grid["rows"], [])
        self.assertEqual(grid["total"], 0.0)

    def test_the_name_reads_as_a_week(self):
        line = self._line()
        self.assertIn(self.employee.name, line.sheet_id.display_name)
