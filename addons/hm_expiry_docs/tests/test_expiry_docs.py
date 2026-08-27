# Part of hm_expiry_docs. See LICENSE file for full copyright and licensing details.
"""Tests for expiring documents.

The behaviour worth guarding is the part people rely on without checking: that
a reminder actually reaches somebody, exactly once, and that the status does
not go stale as the calendar moves.
"""

from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import common, new_test_user, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class ExpiryCase(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.context_today(cls.env["hm.expiry.document"])
        cls.officer = new_test_user(cls.env, login="expiry_officer")
        cls.Document = cls.env["hm.expiry.document"]
        cls.doc_type = cls.env["hm.expiry.document.type"].create({
            "name": "Work Permit",
            "validity_months": 12,
            "reminder_days": 30,
        })

    def _document(self, days_from_today=365, **values):
        data = {
            "name": "WP-001",
            "type_id": self.doc_type.id,
            "date_expiry": self.today + timedelta(days=days_from_today),
            "responsible_id": self.officer.id,
        }
        data.update(values)
        return self.Document.create(data)


class TestStatus(ExpiryCase):

    def test_valid_when_far_off(self):
        self.assertEqual(self._document(365).state, "valid")

    def test_expiring_inside_the_reminder_window(self):
        self.assertEqual(self._document(10).state, "expiring")

    def test_expiring_exactly_on_the_boundary(self):
        """Thirty days out with a thirty-day window counts as expiring."""
        self.assertEqual(self._document(30).state, "expiring")

    def test_valid_one_day_outside_the_window(self):
        self.assertEqual(self._document(31).state, "valid")

    def test_expired_when_past(self):
        self.assertEqual(self._document(-1).state, "expired")

    def test_days_left_goes_negative(self):
        self.assertEqual(self._document(-5).days_to_expiry, -5)

    def test_reminder_window_follows_the_type(self):
        urgent = self.env["hm.expiry.document.type"].create({
            "name": "Insurance", "reminder_days": 90,
        })
        document = self._document(60, type_id=urgent.id)
        self.assertEqual(document.state, "expiring")


class TestStatusStaysCurrent(ExpiryCase):
    """state is stored, so it does not change on its own as time passes."""

    def test_cron_refreshes_a_stale_status(self):
        document = self._document(365)
        self.assertEqual(document.state, "valid")

        # Move the expiry inside the window behind the compute's back, the way
        # the passage of time would.
        self.env.cr.execute(
            "UPDATE hm_expiry_document SET date_expiry = %s WHERE id = %s",
            (self.today + timedelta(days=5), document.id),
        )
        self.env.invalidate_all()
        self.assertEqual(
            document.state, "valid",
            "precondition: the stored status is now stale",
        )

        self.Document._cron_raise_reminders()
        self.assertEqual(
            document.state, "expiring",
            "the cron did not refresh the stored status",
        )


class TestReminders(ExpiryCase):

    def _activities(self, document):
        return self.env["mail.activity"].search([
            ("res_model", "=", "hm.expiry.document"),
            ("res_id", "=", document.id),
        ])

    def test_reminder_raised_for_an_expiring_document(self):
        document = self._document(10)
        self.Document._cron_raise_reminders()

        activities = self._activities(document)
        self.assertTrue(activities)
        self.assertEqual(activities.user_id, self.officer)

    def test_reminder_raised_for_an_expired_document(self):
        document = self._document(-3)
        self.Document._cron_raise_reminders()
        self.assertTrue(self._activities(document))

    def test_no_reminder_while_it_is_far_off(self):
        document = self._document(365)
        self.Document._cron_raise_reminders()
        self.assertFalse(self._activities(document))

    def test_reminder_is_raised_only_once(self):
        """Otherwise the responsible person gets the same activity every
        morning, which is how reminders get ignored."""
        document = self._document(10)
        self.Document._cron_raise_reminders()
        self.Document._cron_raise_reminders()
        self.Document._cron_raise_reminders()
        self.assertEqual(len(self._activities(document)), 1)

    def test_changing_the_expiry_arms_the_reminder_again(self):
        document = self._document(10)
        self.Document._cron_raise_reminders()
        self.assertTrue(document.reminder_sent)

        document.date_expiry = self.today + timedelta(days=400)
        self.assertFalse(
            document.reminder_sent,
            "a new expiry date should re-arm the reminder",
        )
        self.assertFalse(
            self._activities(document),
            "the old reminder should have been withdrawn",
        )

    def test_cancelled_documents_are_not_reminded(self):
        document = self._document(5)
        document.action_mark_cancelled()
        self.Document._cron_raise_reminders()
        self.assertFalse(self._activities(document))

    def test_document_without_a_responsible_is_skipped(self):
        document = self._document(5, responsible_id=False)
        self.Document._cron_raise_reminders()
        self.assertFalse(self._activities(document))


class TestRenewal(ExpiryCase):

    def test_renewing_closes_the_old_document(self):
        old = self._document(10)
        new = self.Document.create({
            "name": "WP-002",
            "type_id": self.doc_type.id,
            "date_expiry": self.today + timedelta(days=400),
            "renewed_from_id": old.id,
        })
        self.assertEqual(old.state, "renewed")
        self.assertEqual(new.renewed_from_id, old)
        self.assertIn(new, old.renewal_ids)

    def test_renewing_withdraws_the_old_reminder(self):
        old = self._document(10)
        self.Document._cron_raise_reminders()
        self.assertTrue(self.env["mail.activity"].search([
            ("res_model", "=", "hm.expiry.document"), ("res_id", "=", old.id),
        ]))

        self.Document.create({
            "name": "WP-002",
            "type_id": self.doc_type.id,
            "date_expiry": self.today + timedelta(days=400),
            "renewed_from_id": old.id,
        })
        self.assertFalse(
            self.env["mail.activity"].search([
                ("res_model", "=", "hm.expiry.document"),
                ("res_id", "=", old.id),
            ]),
            "renewing should stop the old document nagging",
        )

    def test_renew_action_carries_the_details_over(self):
        old = self._document(10, subject="Ahmad Shah")
        action = old.action_renew()
        context = action["context"]
        self.assertEqual(context["default_renewed_from_id"], old.id)
        self.assertEqual(context["default_subject"], "Ahmad Shah")
        self.assertEqual(context["default_type_id"], self.doc_type.id)

    def test_cannot_renew_a_closed_document(self):
        document = self._document(10)
        document.action_mark_cancelled()
        with self.assertRaises(UserError):
            document.action_renew()

    def test_reopen(self):
        document = self._document(10)
        document.action_mark_cancelled()
        self.assertEqual(document.state, "cancelled")
        document.action_reopen()
        self.assertEqual(document.state, "expiring")


class TestValidation(ExpiryCase):

    def test_number_required_when_the_type_says_so(self):
        with self.assertRaises(ValidationError):
            self._document(100, name=False)

    def test_number_optional_when_the_type_allows(self):
        loose = self.env["hm.expiry.document.type"].create({
            "name": "Undertaking", "requires_number": False,
        })
        document = self._document(100, name=False, type_id=loose.id)
        self.assertTrue(document)

    @mute_logger("odoo.sql_db")
    def test_expiry_cannot_precede_issue(self):
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self._document(
                    10, date_issue=self.today + timedelta(days=200)
                )

    def test_display_name_identifies_the_holder(self):
        partner = self.env["res.partner"].create({"name": "Ahmad Shah"})
        document = self._document(100, partner_id=partner.id)
        self.assertIn("Ahmad Shah", document.display_name)
        self.assertIn("WP-001", document.display_name)
