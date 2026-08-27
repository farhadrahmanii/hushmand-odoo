# Part of hm_frontdesk. See LICENSE file for full copyright and licensing details.
"""Tests for the visitor register.

The two behaviours worth protecting: that "who is on site" is always correct,
and that a visitor nobody checked out is surfaced rather than silently closed
with a departure time nobody observed.
"""

from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import common, new_test_user, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class FrontDeskCase(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.host = new_test_user(cls.env, login="frontdesk_host")
        cls.Visitor = cls.env["hm.visitor"]

    def _visitor(self, **values):
        data = {
            "name": "Ahmad Shah",
            "organisation": "Ministry of Finance",
            "host_id": self.host.id,
            "purpose": "Budget meeting",
        }
        data.update(values)
        return self.Visitor.create(data)


class TestCheckInOut(FrontDeskCase):

    def test_new_visitor_is_expected(self):
        self.assertEqual(self._visitor().state, "expected")

    def test_check_in_records_the_time(self):
        visitor = self._visitor()
        visitor.action_check_in()
        self.assertEqual(visitor.state, "on_site")
        self.assertTrue(visitor.check_in)
        self.assertFalse(visitor.check_out)

    def test_check_out_records_the_time(self):
        visitor = self._visitor()
        visitor.action_check_in()
        visitor.action_check_out()
        self.assertEqual(visitor.state, "left")
        self.assertTrue(visitor.check_out)

    def test_duration_is_computed(self):
        visitor = self._visitor()
        visitor.action_check_in()
        visitor.check_in = fields.Datetime.now() - timedelta(minutes=90)
        visitor.action_check_out()
        self.assertGreaterEqual(visitor.duration_minutes, 89)
        self.assertLessEqual(visitor.duration_minutes, 91)

    def test_cannot_check_in_twice(self):
        visitor = self._visitor()
        visitor.action_check_in()
        with self.assertRaises(UserError):
            visitor.action_check_in()

    def test_cannot_check_out_someone_who_never_arrived(self):
        with self.assertRaises(UserError):
            self._visitor().action_check_out()

    def test_cannot_check_in_someone_who_already_left(self):
        """A second visit is a second record, so the register keeps both."""
        visitor = self._visitor()
        visitor.action_check_in()
        visitor.action_check_out()
        with self.assertRaises(UserError):
            visitor.action_check_in()

    def test_cannot_cancel_someone_on_site(self):
        """They are in the building; cancelling would say otherwise."""
        visitor = self._visitor()
        visitor.action_check_in()
        with self.assertRaises(UserError):
            visitor.action_cancel()

    def test_reset_clears_the_timings(self):
        visitor = self._visitor()
        visitor.action_check_in()
        visitor.action_check_out()
        visitor.action_reset_expected()
        self.assertEqual(visitor.state, "expected")
        self.assertFalse(visitor.check_in)
        self.assertFalse(visitor.check_out)


class TestWhoIsOnSite(FrontDeskCase):
    """The question asked during a drill, which has to be right."""

    def test_count_reflects_arrivals_and_departures(self):
        before = self.Visitor.on_site_count()

        first = self._visitor(name="First")
        second = self._visitor(name="Second")
        first.action_check_in()
        second.action_check_in()
        self.assertEqual(self.Visitor.on_site_count(), before + 2)

        first.action_check_out()
        self.assertEqual(self.Visitor.on_site_count(), before + 1)

    def test_expected_visitors_are_not_counted_as_present(self):
        before = self.Visitor.on_site_count()
        self._visitor()
        self.assertEqual(self.Visitor.on_site_count(), before)

    def test_cancelled_visitors_are_not_counted(self):
        before = self.Visitor.on_site_count()
        visitor = self._visitor()
        visitor.action_cancel()
        self.assertEqual(self.Visitor.on_site_count(), before)


class TestNeverCheckedOut(FrontDeskCase):

    def _activities(self, visitor):
        return self.env["mail.activity"].search([
            ("res_model", "=", "hm.visitor"),
            ("res_id", "=", visitor.id),
        ])

    def test_overnight_visitor_is_flagged_to_the_host(self):
        visitor = self._visitor()
        visitor.action_check_in()
        visitor.check_in = fields.Datetime.now() - timedelta(days=2)

        self.Visitor._cron_flag_overnight_visitors()

        activities = self._activities(visitor)
        self.assertTrue(activities)
        self.assertEqual(activities.user_id, self.host)

    def test_the_visitor_is_not_closed_automatically(self):
        """Inventing a departure time nobody observed would make the register
        look tidy and be wrong."""
        visitor = self._visitor()
        visitor.action_check_in()
        visitor.check_in = fields.Datetime.now() - timedelta(days=2)

        self.Visitor._cron_flag_overnight_visitors()

        self.assertEqual(visitor.state, "on_site")
        self.assertFalse(visitor.check_out)

    def test_todays_visitors_are_not_flagged(self):
        visitor = self._visitor()
        visitor.action_check_in()
        self.Visitor._cron_flag_overnight_visitors()
        self.assertFalse(self._activities(visitor))

    def test_departed_visitors_are_not_flagged(self):
        visitor = self._visitor()
        visitor.action_check_in()
        visitor.check_in = fields.Datetime.now() - timedelta(days=2)
        visitor.action_check_out()
        self.Visitor._cron_flag_overnight_visitors()
        self.assertFalse(self._activities(visitor))


class TestHostNotification(FrontDeskCase):

    def test_host_is_told_on_arrival(self):
        visitor = self._visitor()
        before = len(visitor.message_ids)
        visitor.action_check_in()
        self.assertGreater(len(visitor.message_ids), before)

    def test_arrival_without_a_host_does_not_fail(self):
        visitor = self._visitor(host_id=False)
        visitor.action_check_in()
        self.assertEqual(visitor.state, "on_site")


class TestDetails(FrontDeskCase):

    def test_display_name_includes_the_organisation(self):
        visitor = self._visitor()
        self.assertIn("Ahmad Shah", visitor.display_name)
        self.assertIn("Ministry of Finance", visitor.display_name)

    def test_display_name_without_an_organisation(self):
        visitor = self._visitor(organisation=False)
        self.assertEqual(visitor.display_name, "Ahmad Shah")

    @mute_logger("odoo.sql_db")
    def test_accompanying_cannot_be_negative(self):
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self._visitor(accompanying_count=-1)
