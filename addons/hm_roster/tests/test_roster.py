# Part of hm_roster. See LICENSE file for full copyright and licensing details.
"""Tests for shift rosters.

Two things a spreadsheet roster always eventually gets wrong: somebody on two
shifts at once, and a night nobody is covering. Both are what these tests are
for. The third is night shifts crossing midnight, which is where naive
implementations compute a negative duration.
"""

from odoo.exceptions import UserError, ValidationError
from odoo.tests import common, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class RosterCase(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guard_a = cls.env["hr.employee"].create({"name": "Guard A"})
        cls.guard_b = cls.env["hr.employee"].create({"name": "Guard B"})
        cls.day_shift = cls.env["hm.shift.template"].create({
            "name": "Day", "hour_from": 8.0, "hour_to": 16.0,
        })
        cls.night_shift = cls.env["hm.shift.template"].create({
            "name": "Night", "hour_from": 18.0, "hour_to": 6.0,
        })
        cls.Roster = cls.env["hm.roster"]
        cls.Shift = cls.env["hm.roster.shift"]

    def _roster(self, **values):
        data = {
            "name": "Main gate",
            "date_from": "2026-09-01",
            "date_to": "2026-09-30",
            "location": "Main gate",
        }
        data.update(values)
        return self.Roster.create(data)

    def _shift(self, roster, date="2026-09-01", employee=None,
               hour_from=8.0, hour_to=16.0, **values):
        data = {
            "roster_id": roster.id,
            "date": date,
            "hour_from": hour_from,
            "hour_to": hour_to,
            "employee_id": employee.id if employee else False,
        }
        data.update(values)
        return self.Shift.create(data)


class TestNightShifts(RosterCase):
    """A shift from 18:00 to 06:00 ends the next day."""

    def test_template_knows_it_crosses_midnight(self):
        self.assertTrue(self.night_shift.crosses_midnight)
        self.assertFalse(self.day_shift.crosses_midnight)

    def test_template_duration_is_positive(self):
        self.assertAlmostEqual(self.night_shift.duration_hours, 12.0, places=2)
        self.assertAlmostEqual(self.day_shift.duration_hours, 8.0, places=2)

    def test_shift_ends_on_the_following_day(self):
        roster = self._roster()
        shift = self._shift(roster, hour_from=18.0, hour_to=6.0)
        self.assertEqual(shift.start_datetime.day, 1)
        self.assertEqual(shift.end_datetime.day, 2)
        self.assertAlmostEqual(shift.duration_hours, 12.0, places=2)

    def test_day_shift_stays_on_one_day(self):
        roster = self._roster()
        shift = self._shift(roster, hour_from=8.0, hour_to=16.0)
        self.assertEqual(shift.start_datetime.day, shift.end_datetime.day)
        self.assertAlmostEqual(shift.duration_hours, 8.0, places=2)

    def test_half_hour_boundaries(self):
        roster = self._roster()
        shift = self._shift(roster, hour_from=8.5, hour_to=16.5)
        self.assertEqual(shift.start_datetime.minute, 30)
        self.assertAlmostEqual(shift.duration_hours, 8.0, places=2)


class TestDoubleBooking(RosterCase):
    """Nobody works two places at once."""

    def test_overlapping_shifts_are_refused(self):
        roster = self._roster()
        self._shift(roster, employee=self.guard_a, hour_from=8.0, hour_to=16.0)
        with self.assertRaises(ValidationError):
            self._shift(
                roster, employee=self.guard_a, hour_from=14.0, hour_to=22.0
            )

    def test_a_night_shift_clashing_into_the_next_morning_is_caught(self):
        """The overlap a naive check misses, because the clash is on a
        different calendar date from the shift that causes it."""
        roster = self._roster()
        self._shift(
            roster, date="2026-09-01", employee=self.guard_a,
            hour_from=18.0, hour_to=6.0,
        )
        with self.assertRaises(ValidationError):
            self._shift(
                roster, date="2026-09-02", employee=self.guard_a,
                hour_from=4.0, hour_to=12.0,
            )

    def test_back_to_back_shifts_are_allowed(self):
        """Ending at 16:00 and starting at 16:00 is not an overlap."""
        roster = self._roster()
        self._shift(roster, employee=self.guard_a, hour_from=8.0, hour_to=16.0)
        second = self._shift(
            roster, employee=self.guard_a, hour_from=16.0, hour_to=22.0
        )
        self.assertTrue(second)

    def test_different_people_may_share_a_slot(self):
        roster = self._roster()
        self._shift(roster, employee=self.guard_a)
        second = self._shift(roster, employee=self.guard_b)
        self.assertTrue(second)

    def test_unassigned_shifts_never_clash(self):
        roster = self._roster()
        self._shift(roster)
        second = self._shift(roster)
        self.assertTrue(second)

    def test_same_person_on_different_days_is_fine(self):
        roster = self._roster()
        self._shift(roster, date="2026-09-01", employee=self.guard_a)
        second = self._shift(roster, date="2026-09-02", employee=self.guard_a)
        self.assertTrue(second)


class TestPublishing(RosterCase):

    def test_cannot_publish_an_empty_roster(self):
        with self.assertRaises(UserError):
            self._roster().action_publish()

    def test_publishing_refuses_while_shifts_are_uncovered(self):
        """The exact roster that gets published by accident."""
        roster = self._roster()
        self._shift(roster, employee=self.guard_a)
        self._shift(roster, date="2026-09-02")

        self.assertEqual(roster.unassigned_count, 1)
        with self.assertRaises(UserError):
            roster.action_publish()
        self.assertEqual(roster.state, "draft")

    def test_publishing_with_gaps_is_a_separate_deliberate_action(self):
        roster = self._roster()
        self._shift(roster, employee=self.guard_a)
        self._shift(roster, date="2026-09-02")

        roster.action_publish_with_gaps()
        self.assertEqual(roster.state, "published")

    def test_a_fully_covered_roster_publishes(self):
        roster = self._roster()
        self._shift(roster, employee=self.guard_a)
        self._shift(roster, date="2026-09-02", employee=self.guard_b)

        roster.action_publish()
        self.assertEqual(roster.state, "published")
        self.assertEqual(roster.unassigned_count, 0)

    def test_close_and_reopen(self):
        roster = self._roster()
        self._shift(roster, employee=self.guard_a)
        roster.action_publish()
        roster.action_reset_draft()
        self.assertEqual(roster.state, "draft")

        roster.action_publish()
        roster.action_close()
        self.assertEqual(roster.state, "closed")
        with self.assertRaises(UserError):
            roster.action_reset_draft()

    def test_cannot_publish_twice(self):
        roster = self._roster()
        self._shift(roster, employee=self.guard_a)
        roster.action_publish()
        with self.assertRaises(UserError):
            roster.action_publish()


class TestRosterBounds(RosterCase):

    def test_a_shift_outside_the_period_is_refused(self):
        roster = self._roster()
        with self.assertRaises(ValidationError):
            self._shift(roster, date="2026-10-15")

    @mute_logger("odoo.sql_db")
    def test_roster_cannot_end_before_it_starts(self):
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self._roster(date_from="2026-09-30", date_to="2026-09-01")

    def test_counts(self):
        roster = self._roster()
        self._shift(roster, employee=self.guard_a)
        self._shift(roster, date="2026-09-02")
        roster.invalidate_recordset(["shift_count", "unassigned_count"])
        self.assertEqual(roster.shift_count, 2)
        self.assertEqual(roster.unassigned_count, 1)

    def test_template_fills_the_hours(self):
        roster = self._roster()
        shift = self.Shift.new({
            "roster_id": roster.id,
            "date": "2026-09-01",
            "template_id": self.night_shift.id,
        })
        shift._onchange_template()
        self.assertAlmostEqual(shift.hour_from, 18.0, places=2)
        self.assertAlmostEqual(shift.hour_to, 6.0, places=2)
