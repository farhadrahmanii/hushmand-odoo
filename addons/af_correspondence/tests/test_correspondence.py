# Part of af_correspondence. See LICENSE file for full copyright and licensing details.
"""Tests for the maktoob register.

The register's value is its sequence. Numbers issued in order, in two separate
series, and a record that cannot be quietly rewritten afterwards — those are
the properties worth testing.
"""

from odoo.exceptions import UserError
from odoo.tests import common, new_test_user, tagged


@tagged("post_install", "-at_install")
class CorrespondenceCase(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.clerk = new_test_user(cls.env, login="registry_clerk")
        cls.ministry = cls.env["res.partner"].create({
            "name": "Ministry of Finance", "is_company": True,
        })
        cls.Letter = cls.env["af.correspondence"]

    def _letter(self, direction="incoming", **values):
        data = {
            "direction": direction,
            "subject": "Budget allocation query",
            "partner_id": self.ministry.id,
        }
        data.update(values)
        return self.Letter.create(data)


class TestNumbering(CorrespondenceCase):

    def test_incoming_gets_an_incoming_number(self):
        letter = self._letter("incoming")
        self.assertIn("IN/", letter.name)

    def test_outgoing_gets_an_outgoing_number(self):
        letter = self._letter("outgoing")
        self.assertIn("OUT/", letter.name)

    def test_the_two_series_are_independent(self):
        """A paper register keeps two books, each starting at one."""
        first_in = self._letter("incoming")
        first_out = self._letter("outgoing")
        second_in = self._letter("incoming")

        self.assertNotEqual(first_in.name, first_out.name)
        self.assertNotEqual(first_in.name, second_in.name)
        self.assertTrue(first_in.name.startswith("IN/"))
        self.assertTrue(first_out.name.startswith("OUT/"))

    def test_numbers_are_issued_in_order(self):
        letters = [self._letter("incoming") for _ in range(3)]
        numbers = [letter.name for letter in letters]
        self.assertEqual(numbers, sorted(numbers))
        self.assertEqual(len(set(numbers)), 3)

    def test_direction_cannot_be_changed_after_registering(self):
        """The number comes from the series, so switching direction would
        leave a letter carrying a number from the wrong book."""
        letter = self._letter("incoming")
        with self.assertRaises(UserError):
            letter.direction = "outgoing"

    def test_writing_the_same_direction_is_not_blocked(self):
        letter = self._letter("incoming")
        letter.write({"direction": "incoming", "subject": "Amended"})
        self.assertEqual(letter.subject, "Amended")


class TestLifecycle(CorrespondenceCase):

    def test_flow(self):
        letter = self._letter()
        self.assertEqual(letter.state, "registered")
        letter.action_start()
        self.assertEqual(letter.state, "in_progress")
        letter.action_mark_answered()
        self.assertEqual(letter.state, "answered")
        letter.action_close()
        self.assertEqual(letter.state, "closed")

    def test_a_closed_letter_cannot_be_cancelled(self):
        """The register records what happened; it is not a scratchpad."""
        letter = self._letter()
        letter.action_close()
        with self.assertRaises(UserError):
            letter.action_cancel()

    def test_cannot_start_twice(self):
        letter = self._letter()
        letter.action_start()
        with self.assertRaises(UserError):
            letter.action_start()

    def test_cancel_then_reset(self):
        letter = self._letter()
        letter.action_cancel()
        self.assertEqual(letter.state, "cancelled")
        letter.action_reset()
        self.assertEqual(letter.state, "registered")


class TestReplies(CorrespondenceCase):

    def test_reply_action_prepares_an_outgoing_letter(self):
        incoming = self._letter("incoming")
        action = incoming.action_draft_reply()
        context = action["context"]

        self.assertEqual(context["default_direction"], "outgoing")
        self.assertEqual(context["default_reply_to_id"], incoming.id)
        self.assertEqual(context["default_partner_id"], self.ministry.id)
        self.assertIn("Re:", context["default_subject"])

    def test_only_incoming_letters_are_replied_to(self):
        outgoing = self._letter("outgoing")
        with self.assertRaises(UserError):
            outgoing.action_draft_reply()

    def test_reply_links_both_ways(self):
        incoming = self._letter("incoming")
        reply = self._letter(
            "outgoing", subject="Re: query", reply_to_id=incoming.id
        )
        self.assertEqual(reply.reply_to_id, incoming)
        self.assertIn(reply, incoming.reply_ids)
        incoming.invalidate_recordset(["reply_count"])
        self.assertEqual(incoming.reply_count, 1)


class TestRegisterDetails(CorrespondenceCase):

    def test_letter_date_is_separate_from_register_date(self):
        """A letter written on the 1st may not arrive until the 10th, and the
        register records when it arrived."""
        letter = self._letter(
            date="2026-08-10", letter_date="2026-08-01"
        )
        self.assertNotEqual(letter.date, letter.letter_date)

    def test_correspondent_can_be_free_text(self):
        """A one-off letter from a district office does not justify creating
        a contact record."""
        letter = self._letter(
            partner_id=False, correspondent_name="Nangarhar District Office"
        )
        self.assertFalse(letter.partner_id)
        self.assertEqual(
            letter.correspondent_name, "Nangarhar District Office"
        )

    def test_display_name_leads_with_the_number(self):
        letter = self._letter()
        self.assertTrue(letter.display_name.startswith(letter.name))
        self.assertIn("Budget allocation", letter.display_name)

    def test_assignment(self):
        letter = self._letter(assigned_to_id=self.clerk.id)
        self.assertEqual(letter.assigned_to_id, self.clerk)
