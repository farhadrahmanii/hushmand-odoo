# Part of hm_purchase_request. See LICENSE file for full copyright and licensing details.
"""Tests for purchase requests.

These also close the coverage gap left by hm_approvals: that module's engine
was tested on its own, but nothing inherited hm.approval.mixin. This model
does, so the mixin's submit, approve and reject path is exercised end to end
for the first time here.
"""

from odoo.exceptions import UserError
from odoo.tests import common, new_test_user, tagged


@tagged("post_install", "-at_install")
class PurchaseRequestCase(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = new_test_user(
            cls.env, login="pr_manager", groups="base.group_user"
        )
        cls.director = new_test_user(
            cls.env, login="pr_director", groups="base.group_user"
        )
        cls.requester = new_test_user(
            cls.env, login="pr_requester", groups="base.group_user"
        )
        cls.vendor = cls.env["res.partner"].create({
            "name": "Test Vendor", "is_company": True,
        })
        cls.Request = cls.env["hm.purchase.request"]

    def _process(self, steps=None):
        model = self.env["ir.model"]._get("hm.purchase.request")
        steps = steps or [{
            "name": "Manager", "sequence": 10,
            "approver_type": "user", "approver_user_id": self.manager.id,
        }]
        return self.env["hm.approval.process"].create({
            "name": "Purchase request approval",
            "model_id": model.id,
            "step_ids": [(0, 0, values) for values in steps],
        })

    def _request(self, lines=True, **values):
        data = {
            "requester_id": self.requester.id,
            "vendor_id": self.vendor.id,
        }
        data.update(values)
        if lines:
            data["line_ids"] = [(0, 0, {
                "name": "Office chairs",
                "product_qty": 10,
                "price_unit": 45.0,
            })]
        return self.Request.create(data)


class TestBasics(PurchaseRequestCase):

    def test_reference_generated(self):
        request = self._request()
        self.assertIn("PR/", request.name)

    def test_total_is_summed(self):
        request = self._request()
        self.assertAlmostEqual(request.amount_total, 450.0, places=2)

    def test_total_updates_with_the_lines(self):
        request = self._request()
        request.line_ids[0].product_qty = 20
        self.assertAlmostEqual(request.amount_total, 900.0, places=2)

    def test_quantity_must_be_positive(self):
        request = self._request()
        with self.assertRaises(Exception):
            with self.cr.savepoint():
                request.line_ids[0].product_qty = 0

    def test_cannot_submit_without_items(self):
        request = self._request(lines=False)
        self._process()
        with self.assertRaises(UserError):
            request.action_submit()

    def test_cannot_submit_without_a_process(self):
        """A clear message beats a request silently going nowhere."""
        request = self._request()
        with self.assertRaises(UserError):
            request.action_submit()


class TestApprovalIntegration(PurchaseRequestCase):
    """The first real exercise of hm.approval.mixin on an inheriting model."""

    def test_submit_starts_an_approval(self):
        self._process()
        request = self._request()
        request.action_submit()

        self.assertEqual(request.state, "to_approve")
        self.assertTrue(request.approval_request_id)
        self.assertEqual(request.approval_state, "pending")
        self.assertEqual(request.approval_current_step, "Manager")

    def test_approval_hook_moves_the_document(self):
        """The engine calls back into the document. Without this the request
        would be approved but still show as waiting."""
        self._process()
        request = self._request()
        request.action_submit()

        request.approval_request_id.with_user(self.manager).approve()

        self.assertEqual(request.approval_state, "approved")
        self.assertEqual(
            request.state, "approved",
            "the _on_approval_approved hook did not fire",
        )

    def test_rejection_hook_moves_the_document(self):
        self._process()
        request = self._request()
        request.action_submit()

        request.approval_request_id.with_user(self.manager).reject("Too costly")

        self.assertEqual(request.state, "rejected")

    def test_two_steps_in_order(self):
        self._process(steps=[
            {"name": "Manager", "sequence": 10,
             "approver_type": "user", "approver_user_id": self.manager.id},
            {"name": "Director", "sequence": 20,
             "approver_type": "user", "approver_user_id": self.director.id},
        ])
        request = self._request()
        request.action_submit()

        request.approval_request_id.with_user(self.manager).approve()
        self.assertEqual(request.state, "to_approve")
        self.assertEqual(request.approval_current_step, "Director")

        request.approval_request_id.with_user(self.director).approve()
        self.assertEqual(request.state, "approved")

    def test_conditional_step_skipped_for_a_small_request(self):
        """A single process handling both sizes, which is the point of
        conditional steps."""
        self._process(steps=[
            {"name": "Manager", "sequence": 10,
             "approver_type": "user", "approver_user_id": self.manager.id},
            {"name": "Director", "sequence": 20,
             "approver_type": "user", "approver_user_id": self.director.id,
             "condition_field": "amount_total",
             "condition_operator": ">", "condition_value": "1000"},
        ])
        small = self._request()
        small.action_submit()
        small.approval_request_id.with_user(self.manager).approve()
        self.assertEqual(small.state, "approved")

    def test_conditional_step_applies_to_a_large_request(self):
        self._process(steps=[
            {"name": "Manager", "sequence": 10,
             "approver_type": "user", "approver_user_id": self.manager.id},
            {"name": "Director", "sequence": 20,
             "approver_type": "user", "approver_user_id": self.director.id,
             "condition_field": "amount_total",
             "condition_operator": ">", "condition_value": "1000"},
        ])
        large = self._request()
        large.line_ids[0].price_unit = 500.0
        large.action_submit()
        large.approval_request_id.with_user(self.manager).approve()
        self.assertEqual(large.state, "to_approve")
        self.assertEqual(large.approval_current_step, "Director")

    def test_dynamic_approver_from_the_document(self):
        self._process(steps=[{
            "name": "Requester's own check", "sequence": 10,
            "approver_type": "field", "approver_field": "requester_id",
        }])
        request = self._request()
        request.action_submit()
        self.assertEqual(
            request.approval_request_id.current_line_id.approver_ids,
            self.requester,
        )

    def test_approval_can_act_flag(self):
        self._process()
        request = self._request()
        request.action_submit()

        self.assertTrue(request.with_user(self.manager).approval_can_act)
        self.assertFalse(request.with_user(self.director).approval_can_act)

    def test_cancelling_cancels_the_approval(self):
        self._process()
        request = self._request()
        request.action_submit()
        request.action_cancel()

        self.assertEqual(request.state, "cancelled")
        self.assertEqual(request.approval_request_id.state, "cancelled")

    def test_reset_draft_after_rejection_clears_the_old_approval(self):
        self._process()
        request = self._request()
        request.action_submit()
        request.approval_request_id.with_user(self.manager).reject("No")

        request.action_reset_draft()
        self.assertEqual(request.state, "draft")
        self.assertFalse(
            request.approval_request_id,
            "a resubmitted request must start a fresh approval",
        )

    def test_can_resubmit_after_reset(self):
        self._process()
        request = self._request()
        request.action_submit()
        request.approval_request_id.with_user(self.manager).reject("No")
        request.action_reset_draft()
        request.action_submit()
        self.assertEqual(request.state, "to_approve")


class TestBecomingAPurchase(PurchaseRequestCase):

    def _approved_request(self):
        self._process()
        request = self._request()
        request.action_submit()
        request.approval_request_id.with_user(self.manager).approve()
        return request

    def test_cannot_order_before_approval(self):
        self._process()
        request = self._request()
        with self.assertRaises(UserError):
            request.action_create_rfq()

    def test_create_rfq(self):
        request = self._approved_request()
        request.action_create_rfq()

        order = request.purchase_order_ids
        self.assertEqual(len(order), 1)
        self.assertEqual(order.partner_id, self.vendor)
        self.assertEqual(order.origin, request.name)
        self.assertEqual(request.state, "purchased")

    def test_rfq_carries_the_items(self):
        request = self._approved_request()
        request.action_create_rfq()

        line = request.purchase_order_ids.order_line
        self.assertEqual(len(line), 1)
        self.assertAlmostEqual(line.product_qty, 10.0, places=2)
        self.assertAlmostEqual(line.price_unit, 45.0, places=2)

    def test_rfq_needs_a_vendor(self):
        self._process()
        request = self._request(vendor_id=False)
        request.action_submit()
        request.approval_request_id.with_user(self.manager).approve()
        with self.assertRaises(UserError):
            request.action_create_rfq()

    def test_order_links_back_to_the_request(self):
        request = self._approved_request()
        request.action_create_rfq()
        self.assertEqual(
            request.purchase_order_ids.hm_request_id, request
        )
        self.assertEqual(request.purchase_order_count, 1)
