# Part of af_procurement. See LICENSE file for full copyright and licensing details.
"""Tests for the comparative form.

Everything here protects one property: that a completed comparison can answer
"why this supplier" without anybody having to remember. The rules exist
because of what an auditor asks, so the tests are written the same way.
"""

from odoo.exceptions import UserError, ValidationError
from odoo.tests import common, new_test_user, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class ComparativeCase(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = new_test_user(cls.env, login="af_proc_manager")
        cls.cheap = cls.env["res.partner"].create({"name": "Cheap Supplier"})
        cls.dear = cls.env["res.partner"].create({"name": "Dear Supplier"})
        cls.Form = cls.env["af.comparative.form"]

        process = cls.env["hm.approval.process"].create({
            "name": "PR approval",
            "model_id": cls.env["ir.model"]._get("hm.purchase.request").id,
            "step_ids": [(0, 0, {
                "name": "Manager",
                "approver_type": "user",
                "approver_user_id": cls.manager.id,
            })],
        })
        cls.process = process

        cls.request = cls.env["hm.purchase.request"].create({
            "vendor_id": cls.cheap.id,
            "line_ids": [(0, 0, {
                "name": "Generator, 10kVA",
                "product_qty": 1,
                "price_unit": 3000.0,
            })],
        })
        cls.request.action_submit()

    def _form(self, quotes=((1000.0, "cheap"), (1500.0, "dear"))):
        form = self.Form.create({
            "name": "Generator comparison",
            "request_id": self.request.id,
        })
        for amount, which in quotes:
            self.env["af.comparative.quote"].create({
                "form_id": form.id,
                "partner_id": (self.cheap if which == "cheap" else self.dear).id,
                "total_amount": amount,
            })
        form.invalidate_recordset()
        return form


class TestTheComparison(ComparativeCase):

    def test_reference_generated(self):
        self.assertIn("CF/", self._form().reference)

    def test_the_lowest_quotation_is_identified(self):
        form = self._form()
        self.assertEqual(form.lowest_quote_id.partner_id, self.cheap)

    def test_choosing_the_lowest_needs_no_explanation(self):
        form = self._form()
        form.selected_quote_id = form.lowest_quote_id
        form.action_done()
        self.assertEqual(form.state, "done")

    def test_choosing_a_dearer_supplier_demands_a_reason(self):
        """The rule the whole module exists for."""
        form = self._form()
        dearer = form.quote_ids.filtered(lambda q: q.partner_id == self.dear)
        form.selected_quote_id = dearer

        self.assertTrue(form.not_lowest)
        with self.assertRaises(UserError):
            form.action_done()

    def test_a_dearer_supplier_with_a_reason_is_accepted(self):
        form = self._form()
        form.selected_quote_id = form.quote_ids.filtered(
            lambda q: q.partner_id == self.dear
        )
        form.selection_reason = "Only supplier able to deliver before Nowruz."
        form.action_done()
        self.assertEqual(form.state, "done")

    def test_whitespace_is_not_a_reason(self):
        form = self._form()
        form.selected_quote_id = form.quote_ids.filtered(
            lambda q: q.partner_id == self.dear
        )
        form.selection_reason = "    "
        with self.assertRaises(UserError):
            form.action_done()

    def test_one_quotation_is_not_a_comparison(self):
        form = self._form(quotes=((1000.0, "cheap"),))
        form.selected_quote_id = form.quote_ids
        with self.assertRaises(UserError):
            form.action_done()

    def test_something_must_be_chosen(self):
        form = self._form()
        with self.assertRaises(UserError):
            form.action_done()

    def test_a_quotation_from_another_comparison_is_refused(self):
        first = self._form()
        second = self._form()
        with self.assertRaises(ValidationError):
            second.selected_quote_id = first.quote_ids[0]


class TestTheRecord(ComparativeCase):

    def _complete(self, dearer=False, reason=None):
        form = self._form()
        target = self.dear if dearer else self.cheap
        form.selected_quote_id = form.quote_ids.filtered(
            lambda q: q.partner_id == target
        )
        if reason:
            form.selection_reason = reason
        form.action_done()
        return form

    def test_the_decision_is_written_to_the_request(self):
        """So the reasoning sits on the document people actually open."""
        before = len(self.request.message_ids)
        self._complete()
        self.assertGreater(len(self.request.message_ids), before)

    def test_the_reason_is_recorded_when_not_lowest(self):
        form = self._complete(
            dearer=True, reason="Only supplier with parts in country."
        )
        bodies = " ".join(form.message_ids.mapped("body"))
        self.assertIn("parts in country", bodies)

    def test_a_completed_comparison_cannot_be_cancelled(self):
        """It is part of the record of how the supplier was chosen."""
        form = self._complete()
        with self.assertRaises(UserError):
            form.action_cancel()

    def test_completing_twice_is_refused(self):
        form = self._complete()
        with self.assertRaises(UserError):
            form.action_done()

    def test_applying_the_result_sets_the_supplier(self):
        form = self._complete(
            dearer=True, reason="Delivery time.",
        )
        form.action_apply_to_request()
        self.assertEqual(self.request.vendor_id, self.dear)

    def test_cannot_apply_an_incomplete_comparison(self):
        form = self._form()
        with self.assertRaises(UserError):
            form.action_apply_to_request()


class TestQuotations(ComparativeCase):

    def test_selected_flag_follows_the_choice(self):
        form = self._form()
        cheapest = form.lowest_quote_id
        form.selected_quote_id = cheapest
        form.invalidate_recordset()
        self.assertTrue(cheapest.is_selected)
        others = form.quote_ids - cheapest
        self.assertFalse(any(others.mapped("is_selected")))

    @mute_logger("odoo.sql_db")
    def test_a_negative_quotation_is_refused(self):
        form = self._form()
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.env["af.comparative.quote"].create({
                    "form_id": form.id,
                    "partner_id": self.cheap.id,
                    "total_amount": -100.0,
                })

    def test_the_request_counts_its_comparisons(self):
        self._form()
        self._form()
        self.request.invalidate_recordset(["af_comparative_count"])
        self.assertEqual(self.request.af_comparative_count, 2)
