# Part of hm_approvals. See LICENSE file for full copyright and licensing details.
"""Tests for the approval engine.

The engine is exercised against ``res.partner``. That is deliberate: a request
addresses its document by model and id, so it works on any model without that
model knowing anything about approvals, and res.partner is a real model with
chatter and activities rather than a fixture invented for the test.

The mixin's own methods are covered where they do not need a model to inherit
them; full mixin coverage arrives with the first consumer module.
"""

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import common, new_test_user, tagged


@tagged("post_install", "-at_install")
class ApprovalCase(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model = cls.env["ir.model"]._get("res.partner")
        cls.alice = new_test_user(cls.env, login="alice_approver")
        cls.bob = new_test_user(cls.env, login="bob_approver")
        cls.carol = new_test_user(cls.env, login="carol_approver")
        cls.Process = cls.env["hm.approval.process"]
        cls.Request = cls.env["hm.approval.request"]

    def _process(self, steps=None, name="Test process"):
        steps = steps if steps is not None else [
            {"name": "First", "sequence": 10,
             "approver_type": "user", "approver_user_id": self.alice.id},
        ]
        return self.Process.create({
            "name": name,
            "model_id": self.model.id,
            "step_ids": [(0, 0, values) for values in steps],
        })

    def _document(self, **values):
        data = {"name": "Test Document"}
        data.update(values)
        return self.env["res.partner"].create(data)


class TestProcessConfiguration(ApprovalCase):

    def test_process_needs_steps(self):
        with self.assertRaises(ValidationError):
            self.Process.create({"name": "Empty", "model_id": self.model.id})

    def test_step_needs_an_approver(self):
        with self.assertRaises(ValidationError):
            self._process(steps=[{"name": "Nobody", "approver_type": "user"}])

    def test_bad_field_path_is_caught_when_configured(self):
        """A typo should fail while someone is editing the process, not months
        later when a document is submitted."""
        with self.assertRaises(ValidationError):
            self._process(steps=[{
                "name": "Bad path",
                "approver_type": "field",
                "approver_field": "no_such_field.user_id",
            }])

    def test_good_field_path_accepted(self):
        process = self._process(steps=[{
            "name": "Owner",
            "approver_type": "field",
            "approver_field": "user_id",
        }])
        self.assertTrue(process.step_ids)

    def test_unknown_condition_field_rejected(self):
        with self.assertRaises(ValidationError):
            self._process(steps=[{
                "name": "Conditional",
                "approver_type": "user",
                "approver_user_id": self.alice.id,
                "condition_field": "not_a_real_field",
                "condition_operator": "=",
                "condition_value": "1",
            }])


class TestApprovalFlow(ApprovalCase):

    def test_single_step_approval(self):
        process = self._process()
        document = self._document()
        request = self.Request._start(document, process)

        self.assertEqual(request.state, "pending")
        self.assertEqual(request.current_line_id.step_id.name, "First")

        request.with_user(self.alice).approve()
        self.assertEqual(request.state, "approved")
        self.assertTrue(request.date_done)

    def test_steps_run_in_order(self):
        process = self._process(steps=[
            {"name": "Second", "sequence": 20,
             "approver_type": "user", "approver_user_id": self.bob.id},
            {"name": "First", "sequence": 10,
             "approver_type": "user", "approver_user_id": self.alice.id},
        ])
        request = self.Request._start(self._document(), process)

        self.assertEqual(request.current_line_id.step_id.name, "First")
        request.with_user(self.alice).approve()
        self.assertEqual(request.state, "pending")
        self.assertEqual(request.current_line_id.step_id.name, "Second")
        request.with_user(self.bob).approve()
        self.assertEqual(request.state, "approved")

    def test_only_the_named_approver_can_act(self):
        process = self._process()
        request = self.Request._start(self._document(), process)
        with self.assertRaises(AccessError):
            request.with_user(self.bob).approve()

    def test_rejection_stops_the_chain(self):
        process = self._process(steps=[
            {"name": "First", "sequence": 10,
             "approver_type": "user", "approver_user_id": self.alice.id},
            {"name": "Second", "sequence": 20,
             "approver_type": "user", "approver_user_id": self.bob.id},
        ])
        request = self.Request._start(self._document(), process)
        request.with_user(self.alice).reject("Not this time")

        self.assertEqual(request.state, "rejected")
        second = request.line_ids.filtered(lambda l: l.step_id.name == "Second")
        self.assertEqual(
            second.state, "cancelled",
            "later steps must not be left waiting after a rejection",
        )

    def test_rejection_reason_required_by_default(self):
        process = self._process()
        request = self.Request._start(self._document(), process)
        with self.assertRaises(UserError):
            request.with_user(self.alice).reject()

    def test_step_can_forbid_rejection(self):
        process = self._process(steps=[{
            "name": "Notify only", "approver_type": "user",
            "approver_user_id": self.alice.id, "allow_reject": False,
        }])
        request = self.Request._start(self._document(), process)
        with self.assertRaises(UserError):
            request.with_user(self.alice).reject("no")

    def test_comment_can_be_required_on_approval(self):
        process = self._process(steps=[{
            "name": "Explain", "approver_type": "user",
            "approver_user_id": self.alice.id, "require_comment": True,
        }])
        request = self.Request._start(self._document(), process)
        with self.assertRaises(UserError):
            request.with_user(self.alice).approve()
        request.with_user(self.alice).approve("Checked against the budget")
        self.assertEqual(request.state, "approved")

    def test_cannot_approve_a_finished_request(self):
        process = self._process()
        request = self.Request._start(self._document(), process)
        request.with_user(self.alice).approve()
        with self.assertRaises(UserError):
            request.with_user(self.alice).approve()

    def test_cancel(self):
        process = self._process()
        request = self.Request._start(self._document(), process)
        request.action_cancel()
        self.assertEqual(request.state, "cancelled")
        self.assertTrue(
            all(line.state == "cancelled" for line in request.line_ids)
        )


class TestGroupSteps(ApprovalCase):

    def test_anyone_in_the_group_can_approve(self):
        group = self.env["res.groups"].create({"name": "Approvers"})
        group.users = [(6, 0, [self.alice.id, self.bob.id])]
        process = self._process(steps=[{
            "name": "Any manager", "approver_type": "group",
            "approver_group_id": group.id,
        }])
        request = self.Request._start(self._document(), process)

        self.assertEqual(len(request.current_line_id.approver_ids), 2)
        request.with_user(self.bob).approve()
        self.assertEqual(request.state, "approved")
        self.assertEqual(request.line_ids.acted_by_id, self.bob)

    def test_someone_outside_the_group_cannot(self):
        group = self.env["res.groups"].create({"name": "Approvers"})
        group.users = [(6, 0, [self.alice.id])]
        process = self._process(steps=[{
            "name": "Any manager", "approver_type": "group",
            "approver_group_id": group.id,
        }])
        request = self.Request._start(self._document(), process)
        with self.assertRaises(AccessError):
            request.with_user(self.carol).approve()


class TestDynamicApprovers(ApprovalCase):

    def test_approver_resolved_from_the_document(self):
        """The point of a field approver: the process names a relationship,
        not a person, so it survives people changing roles."""
        process = self._process(steps=[{
            "name": "Account manager", "approver_type": "field",
            "approver_field": "user_id",
        }])
        document = self._document(user_id=self.carol.id)
        request = self.Request._start(document, process)

        self.assertEqual(request.current_line_id.approver_ids, self.carol)
        request.with_user(self.carol).approve()
        self.assertEqual(request.state, "approved")

    def test_unresolvable_approver_leaves_the_step_unassigned(self):
        process = self._process(steps=[{
            "name": "Account manager", "approver_type": "field",
            "approver_field": "user_id",
        }])
        request = self.Request._start(self._document(), process)
        self.assertFalse(request.current_line_id.approver_ids)


class TestConditionalSteps(ApprovalCase):

    def _conditional_process(self, operator, value):
        return self._process(steps=[
            {"name": "Always", "sequence": 10,
             "approver_type": "user", "approver_user_id": self.alice.id},
            {"name": "Sometimes", "sequence": 20,
             "approver_type": "user", "approver_user_id": self.bob.id,
             "condition_field": "credit_limit",
             "condition_operator": operator,
             "condition_value": value},
        ])

    def test_step_skipped_when_condition_false(self):
        process = self._conditional_process(">", "1000")
        request = self.Request._start(self._document(credit_limit=500.0), process)
        self.assertEqual(len(request.line_ids), 1)
        request.with_user(self.alice).approve()
        self.assertEqual(request.state, "approved")

    def test_step_included_when_condition_true(self):
        process = self._conditional_process(">", "1000")
        request = self.Request._start(self._document(credit_limit=5000.0), process)
        self.assertEqual(len(request.line_ids), 2)
        request.with_user(self.alice).approve()
        self.assertEqual(request.state, "pending")

    def test_set_and_not_set(self):
        process = self._conditional_process("set", "")
        request = self.Request._start(self._document(credit_limit=1.0), process)
        self.assertEqual(len(request.line_ids), 2)

    def test_all_steps_skipped_completes_immediately(self):
        """Better than leaving a request stuck with nothing to approve."""
        process = self._process(steps=[{
            "name": "Only if huge", "approver_type": "user",
            "approver_user_id": self.alice.id,
            "condition_field": "credit_limit",
            "condition_operator": ">",
            "condition_value": "1000000",
        }])
        request = self.Request._start(self._document(credit_limit=1.0), process)
        self.assertEqual(request.state, "approved")


class TestDocumentIntegration(ApprovalCase):

    def test_decision_is_posted_to_the_document(self):
        """The record of who approved what has to live where people look."""
        process = self._process()
        document = self._document()
        before = len(document.message_ids)

        request = self.Request._start(document, process)
        request.with_user(self.alice).approve("Looks right")

        self.assertGreater(len(document.message_ids), before)
        bodies = " ".join(document.message_ids.mapped("body"))
        self.assertIn("Looks right", bodies)

    def test_approver_gets_an_activity(self):
        process = self._process()
        document = self._document()
        self.Request._start(document, process)

        activities = self.env["mail.activity"].search([
            ("res_model", "=", "res.partner"),
            ("res_id", "=", document.id),
        ])
        self.assertTrue(activities)
        self.assertIn(self.alice, activities.mapped("user_id"))

    def test_activity_withdrawn_once_decided(self):
        process = self._process()
        document = self._document()
        request = self.Request._start(document, process)
        request.with_user(self.alice).approve()

        activities = self.env["mail.activity"].search([
            ("res_model", "=", "res.partner"),
            ("res_id", "=", document.id),
        ])
        self.assertFalse(
            activities, "a decided step must not leave an activity behind"
        )

    def test_process_lookup_by_model(self):
        process = self._process()
        found = self.Process._process_for(self._document())
        self.assertEqual(found, process)

    def test_no_process_for_an_unrelated_model(self):
        self._process()
        company = self.env["res.company"].search([], limit=1)
        self.assertFalse(self.Process._process_for(company))
