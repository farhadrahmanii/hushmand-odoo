# Part of af_liaison. See LICENSE file for full copyright and licensing details.
"""Tests for Afghan liaison documents.

This module adds very little logic of its own, so the tests mostly check that
the thin layer really does sit on the generic engine rather than duplicating
it — and that the six document types a liaison office needs are actually there
after installation.
"""

from datetime import timedelta

from odoo import fields
from odoo.tests import common, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestLiaisonDocuments(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.context_today(cls.env["hm.expiry.document"])
        cls.officer = new_test_user(cls.env, login="liaison_officer")
        cls.employee = cls.env["hr.employee"].create({"name": "Ahmad Shah"})
        cls.visa_type = cls.env.ref("af_liaison.type_visa")
        cls.Document = cls.env["hm.expiry.document"]

    def _document(self, days=20, **values):
        data = {
            "name": "V-1001",
            "type_id": self.visa_type.id,
            "date_expiry": self.today + timedelta(days=days),
            "responsible_id": self.officer.id,
            "employee_id": self.employee.id,
        }
        data.update(values)
        return self.Document.create(data)

    # ------------------------------------------------------------------
    # The six types exist
    # ------------------------------------------------------------------

    def test_all_six_document_types_installed(self):
        expected = [
            "af_liaison.type_visa",
            "af_liaison.type_work_permit",
            "af_liaison.type_vehicle_permit",
            "af_liaison.type_weapon_licence",
            "af_liaison.type_membership_card",
            "af_liaison.type_cip_card",
        ]
        for xml_id in expected:
            with self.subTest(xml_id):
                self.assertTrue(self.env.ref(xml_id))

    def test_weapon_licence_has_the_longest_notice(self):
        """It takes longest to renew, so it warns earliest."""
        weapon = self.env.ref("af_liaison.type_weapon_licence")
        card = self.env.ref("af_liaison.type_membership_card")
        self.assertGreater(weapon.reminder_days, card.reminder_days)

    # ------------------------------------------------------------------
    # The employee link
    # ------------------------------------------------------------------

    def test_document_links_to_an_employee(self):
        document = self._document()
        self.assertEqual(document.employee_id, self.employee)
        self.assertIn(document, self.employee.af_document_ids)
        self.assertEqual(self.employee.af_document_count, 1)

    def test_employee_is_flagged_when_a_document_needs_attention(self):
        self._document(days=10)
        self.employee.invalidate_recordset(
            ["af_document_alert", "af_document_count"]
        )
        self.assertTrue(self.employee.af_document_alert)

    def test_employee_is_not_flagged_for_a_valid_document(self):
        self._document(days=300)
        self.employee.invalidate_recordset(
            ["af_document_alert", "af_document_count"]
        )
        self.assertFalse(self.employee.af_document_alert)

    def test_choosing_an_employee_fills_the_holder(self):
        document = self.Document.new({
            "type_id": self.visa_type.id,
            "employee_id": self.employee.id,
        })
        document._onchange_employee_fills_holder()
        self.assertEqual(document.subject, "Ahmad Shah")

    def test_employee_appears_in_the_document_name(self):
        document = self._document()
        self.assertIn("Ahmad Shah", document.display_name)

    # ------------------------------------------------------------------
    # It really is the generic engine underneath
    # ------------------------------------------------------------------

    def test_reminders_come_from_the_shared_engine(self):
        """No reminder logic is duplicated here; the generic cron drives it."""
        document = self._document(days=10)
        self.Document._cron_raise_reminders()

        activities = self.env["mail.activity"].search([
            ("res_model", "=", "hm.expiry.document"),
            ("res_id", "=", document.id),
        ])
        self.assertTrue(activities)
        self.assertEqual(
            activities.user_id, self.officer,
            "the liaison officer is reminded, not the employee",
        )

    def test_renewal_chain_works_for_a_visa(self):
        old = self._document(days=10)
        new = self.Document.create({
            "name": "V-1002",
            "type_id": self.visa_type.id,
            "date_expiry": self.today + timedelta(days=400),
            "employee_id": self.employee.id,
            "renewed_from_id": old.id,
        })
        self.assertEqual(old.state, "renewed")
        self.assertEqual(new.renewed_from_id, old)

    def test_province_can_be_recorded(self):
        kabul = self.env.ref("af_l10n_base.state_af_kab")
        document = self._document(af_province_id=kabul.id)
        self.assertEqual(document.af_province_id, kabul)
