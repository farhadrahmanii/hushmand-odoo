# Part of hm_expiry_docs. See LICENSE file for full copyright and licensing details.
"""What the licence gate does to a real document, end to end.

hm_license tests the gate against its own abstract mixin, which proves the
decision but not the wiring. This proves the wiring: a concrete model, with
records in a database, behaving the way a lapsed customer would experience it.

Expiring documents are the cheapest gated model in the catalogue to set up,
which is the only reason the test lives here rather than in payroll. What it
demonstrates holds for every gated model, because they all inherit the same
mixin.
"""

from datetime import timedelta

from odoo import fields
from odoo.addons.hm_license.tests.common import LicenceKeyMixin
from odoo.exceptions import UserError
from odoo.tests import common, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestLicenceGate(LicenceKeyMixin, common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.setUpLicenceKeys()
        # The gate stands down under --test-enable so that the rest of the
        # catalogue can create records without a licence. This suite is the
        # end-to-end proof that it does not, so it opts back in.
        cls.Document = cls.env["hm.expiry.document"].with_context(
            hm_licence_gate_live=True
        )
        cls.doc_type = cls.env["hm.expiry.document.type"].create({
            "name": "Work Permit",
            "validity_months": 12,
            "reminder_days": 30,
        })
        cls.env["hm.license"].search([]).unlink()

    def _values(self, **overrides):
        values = {
            "name": "WP-001",
            "type_id": self.doc_type.id,
            "date_expiry": fields.Date.context_today(self.Document)
            + timedelta(days=365),
        }
        values.update(overrides)
        return values

    # ------------------------------------------------------------------
    # Unlicensed
    # ------------------------------------------------------------------

    def test_an_unlicensed_database_cannot_create_documents(self):
        with self.armed():
            with self.assertRaises(UserError) as caught:
                self.Document.create(self._values())
        self.assertIn("No licence", str(caught.exception))

    def test_an_unlicensed_database_cannot_edit_documents(self):
        document = self.Document.create(self._values())
        with self.armed():
            with self.assertRaises(UserError):
                document.name = "WP-002"

    def test_the_customer_keeps_reading_what_they_already_have(self):
        """The gate refuses new work. It does not hold a customer's own
        records hostage -- that turns a late renewal into a dispute, and it is
        the behaviour that gets a supplier talked about."""
        document = self.Document.create(self._values())
        with self.armed():
            self.assertEqual(document.name, "WP-001")
            self.assertEqual(document.type_id, self.doc_type)
            self.assertTrue(self.Document.search([("id", "=", document.id)]))

    def test_the_customer_can_still_delete(self):
        document = self.Document.create(self._values())
        with self.armed():
            document.unlink()
        self.assertFalse(document.exists())

    # ------------------------------------------------------------------
    # Licensed
    # ------------------------------------------------------------------

    def test_a_covering_licence_restores_normal_service(self):
        with self.armed():
            self.install_licence(["hm_expiry_docs"])
            document = self.Document.create(self._values())
            document.name = "WP-002"
        self.assertEqual(document.name, "WP-002")

    def test_a_licence_for_another_module_does_not_help(self):
        with self.armed():
            self.install_licence(["hm_payroll", "af_hr"])
            with self.assertRaises(UserError) as caught:
                self.Document.create(self._values())
        self.assertIn("hm_expiry_docs", str(caught.exception))

    def test_work_continues_through_the_grace_month(self):
        with self.armed():
            self.install_licence(["hm_expiry_docs"], days=-5)
            document = self.Document.create(self._values())
        self.assertTrue(document.exists())

    def test_work_stops_once_the_grace_month_is_over(self):
        with self.armed():
            self.install_licence(["hm_expiry_docs"], days=-90)
            with self.assertRaises(UserError):
                self.Document.create(self._values())

    # ------------------------------------------------------------------
    # As somebody other than the administrator
    # ------------------------------------------------------------------

    def test_an_ordinary_user_is_told_about_the_licence(self):
        """The bug this guards against only appears with two users.

        Refreshing a licence state writes, and a clerk has read access to
        hm.license and nothing else. Checked as the administrator it passes;
        checked as the person who actually files documents it used to raise
        an access error about a model they have never heard of.
        """
        clerk = new_test_user(self.env, login="expiry_clerk")
        with self.armed():
            with self.assertRaises(UserError) as caught:
                self.Document.with_user(clerk).create(self._values())
        self.assertIn("No licence", str(caught.exception))

    def test_an_ordinary_user_can_work_once_licensed(self):
        clerk = new_test_user(self.env, login="expiry_clerk_two")
        with self.armed():
            self.install_licence(["hm_expiry_docs"])
            document = self.Document.with_user(clerk).create(self._values())
        self.assertTrue(document.exists())

    def test_an_ordinary_user_sees_the_indicator(self):
        """The systray reads this over RPC as whoever is logged in."""
        clerk = new_test_user(self.env, login="expiry_clerk_three")
        with self.armed():
            self.install_licence(["hm_expiry_docs"], days=-3)
            status = self.env["hm.license"].with_user(clerk).status()
        self.assertEqual(status["state"], "grace")

    # ------------------------------------------------------------------
    # The state everything else in CI runs in
    # ------------------------------------------------------------------

    def test_an_unarmed_build_is_unaffected(self):
        """Without a vendor key there is nothing to enforce, which is why the
        other 500-odd tests in this catalogue need no licence at all."""
        self.assertTrue(self.Document.create(self._values()).exists())
