# Part of af_hr. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests import common, tagged


@tagged("post_install", "-at_install")
class TestAfEmployeeIdentity(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.kabul = cls.env.ref("af_l10n_base.state_af_kab")
        cls.district = cls.env["af.district"].search(
            [("state_id", "=", cls.kabul.id)], limit=1
        )
        cls.employee = cls.env["hr.employee"].create({
            "name": "Ahmad Shah",
            "af_father_name": "Mohammad Nabi",
            "af_grandfather_name": "Abdul Ghani",
            "af_tin": "9001234567",
        })

    def test_fields_reach_the_employee_through_the_version(self):
        """The fields live on hr.version. Odoo 19 delegates from the employee,
        so they must be readable and writable straight from the employee."""
        self.assertEqual(self.employee.af_father_name, "Mohammad Nabi")
        self.employee.af_father_name = "Mohammad Nabi Khan"
        self.assertEqual(
            self.employee.version_id.af_father_name, "Mohammad Nabi Khan"
        )

    def test_full_identity_reads_the_way_documents_do(self):
        """Afghan names have no surname, so official documents name the father
        and grandfather. This is the string that goes on a letter."""
        self.assertEqual(
            self.employee.af_full_identity,
            "Ahmad Shah, s/o Mohammad Nabi, g/o Abdul Ghani",
        )

    def test_full_identity_without_a_grandfather(self):
        employee = self.env["hr.employee"].create({
            "name": "Zarmina",
            "af_father_name": "Karim",
        })
        self.assertEqual(employee.af_full_identity, "Zarmina, s/o Karim")

    def test_full_identity_with_no_parents_recorded(self):
        employee = self.env["hr.employee"].create({"name": "Solo"})
        self.assertEqual(employee.af_full_identity, "Solo")

    def test_paper_tazkira_reference(self):
        """A paper tazkira is three numbers together, not one serial."""
        self.employee.write({
            "af_tazkira_volume": "12",
            "af_tazkira_page": "340",
            "af_tazkira_register": "56",
        })
        self.assertEqual(
            self.employee.af_tazkira_reference,
            "Volume 12, Page 340, Register 56",
        )

    def test_partial_tazkira_still_renders(self):
        self.employee.af_tazkira_volume = "12"
        self.assertIn("Volume 12", self.employee.af_tazkira_reference)
        self.assertIn("-", self.employee.af_tazkira_reference)

    def test_no_tazkira_reference_when_empty(self):
        self.assertEqual(self.employee.af_tazkira_reference, "")

    def test_addresses_use_the_localization_data(self):
        self.employee.write({
            "private_state_id": self.kabul.id,
            "af_private_district_id": self.district.id,
            "af_permanent_state_id": self.kabul.id,
            "af_permanent_district_id": self.district.id,
        })
        self.assertEqual(self.employee.af_private_district_id, self.district)
        self.assertEqual(self.employee.af_permanent_district_id, self.district)

    def test_district_fills_the_province(self):
        version = self.employee.version_id
        version.af_private_district_id = self.district
        version._onchange_af_private_district()
        self.assertEqual(version.private_state_id, self.kabul)

    def test_changing_province_clears_a_foreign_district(self):
        version = self.employee.version_id
        version.private_state_id = self.kabul
        version.af_private_district_id = self.district
        version.private_state_id = self.env.ref("af_l10n_base.state_af_her")
        version._onchange_af_private_state()
        self.assertFalse(version.af_private_district_id)

    def test_identity_is_versioned_not_overwritten(self):
        """The reason these fields sit on the version: a correction becomes
        history rather than erasing what the record said before."""
        original = self.employee.version_id
        self.assertTrue(original)
        self.assertEqual(original.af_father_name, "Mohammad Nabi")


@tagged("post_install", "-at_install")
class TestDisciplinaryAction(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create({"name": "Test Employee"})
        cls.Discipline = cls.env["af.employee.discipline"]

    def _make(self, **kwargs):
        values = {
            "employee_id": self.employee.id,
            "action_type": "written",
            "reason": "Repeated lateness",
        }
        values.update(kwargs)
        return self.Discipline.create(values)

    def test_reference_is_generated(self):
        record = self._make()
        self.assertNotEqual(record.name, "New")
        self.assertIn("DA/", record.name)

    def test_lifecycle(self):
        record = self._make()
        self.assertEqual(record.state, "draft")
        record.action_issue()
        self.assertEqual(record.state, "issued")
        record.action_acknowledge()
        self.assertEqual(record.state, "acknowledged")
        self.assertTrue(record.acknowledged_date)
        record.action_close()
        self.assertEqual(record.state, "closed")

    def test_acknowledgement_is_recorded_separately(self):
        """Whether the employee actually saw it is the part that matters if
        this is ever challenged."""
        record = self._make()
        record.action_issue()
        self.assertFalse(record.acknowledged_date)
        record.action_acknowledge()
        self.assertTrue(record.acknowledged_date)

    def test_cannot_acknowledge_a_draft(self):
        with self.assertRaises(UserError):
            self._make().action_acknowledge()

    def test_cannot_close_a_draft(self):
        with self.assertRaises(UserError):
            self._make().action_close()

    def test_closed_action_cannot_be_cancelled(self):
        """History has to stay intact; record a new action instead."""
        record = self._make()
        record.action_issue()
        record.action_close()
        with self.assertRaises(UserError):
            record.action_cancel()

    def test_cancel_then_reset(self):
        record = self._make()
        record.action_cancel()
        self.assertEqual(record.state, "cancelled")
        record.action_reset_draft()
        self.assertEqual(record.state, "draft")

    def test_suspension_needs_a_start_date(self):
        with self.assertRaises(UserError):
            self._make(action_type="suspension")

    def test_suspension_with_dates(self):
        record = self._make(
            action_type="suspension",
            suspension_date_from="2026-09-01",
            suspension_date_to="2026-09-07",
        )
        self.assertEqual(record.action_type, "suspension")

    def test_department_follows_the_employee(self):
        department = self.env["hr.department"].create({"name": "Finance"})
        self.employee.department_id = department
        record = self._make()
        self.assertEqual(record.department_id, department)

    def test_count_on_the_employee_ignores_cancelled(self):
        self._make()
        cancelled = self._make(reason="Withdrawn")
        cancelled.action_cancel()
        self.employee.invalidate_recordset(["af_discipline_count"])
        self.assertEqual(self.employee.af_discipline_count, 1)


@tagged("post_install", "-at_install")
class TestIdCardReport(common.TransactionCase):

    def test_report_renders(self):
        employee = self.env["hr.employee"].create({
            "name": "Card Holder",
            "af_father_name": "Father Name",
            "af_tazkira_number": "1401-1234-56789",
        })
        report = self.env.ref("af_hr.action_report_af_id_card")
        html, _report_type = self.env["ir.actions.report"]._render_qweb_html(
            report.report_name, employee.ids
        )
        content = html.decode() if isinstance(html, bytes) else html
        self.assertIn("Card Holder", content)
        self.assertIn("Father Name", content)
        self.assertIn("1401-1234-56789", content)
