# Approval Workflows

Route any Odoo document through a configurable multi-step approval chain.

---

## Why this exists

**Odoo Community has no approval engine at all.**

Enterprise has an Approvals app, but it models *a request for something* — a
standalone record somebody raises, like asking for a laptop. It does not put an
approval chain **in front of a document you already have**, which is what an
organisation actually needs: this purchase request, this leave, this contract,
routed to the right people in the right order before it takes effect.

---

## Setting one up

**Approvals → Configuration → Processes.** Pick a document, add steps, say who
approves each one. No code, and no developer, once the document is connected.

### Three things that let one process do the work of several

**Conditional steps.** A step can carry a condition and is *skipped* when it
does not hold — so one process says "anything over 50,000 also needs the
director" instead of two processes to keep in step with each other.

**Approvers the document decides.** Instead of naming a person, a step can name
a path on the document:

```
employee_id.parent_id.user_id      the requester's manager
project_id.user_id                 whoever runs the project
```

The approver is found from the document itself, so the process survives people
changing roles. A bad path is rejected **when you configure it**, not months
later when someone submits.

**Group steps.** Assign a step to a group and everyone in it is notified.
Whoever acts first decides it; the rest are withdrawn.

---

## What approvers see

A normal **Odoo activity** on the document, and every decision posted to the
document's **chatter**. The record of who approved what lives where people
already look, not buried inside this module.

**Approvals → Waiting on Me** lists everything routed to you.

---

## For developers

```python
class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _inherit = ["purchase.request", "hm.approval.mixin"]

    def _on_approval_approved(self, request):
        self.state = "approved"

    def _on_approval_rejected(self, request):
        self.state = "rejected"
```

That is the whole integration. The mixin adds `approval_state`,
`approval_can_act`, and the submit / approve / reject actions. Steps are
configured by the customer afterwards.

The engine addresses documents by model and id, so it works on any model
without that model knowing anything about approvals.

---

## Two deliberate decisions

**Conditions are a fixed set of operators, never an evaluated expression.** It
would have been easier to store a Python snippet and run it. Configuration that
can execute arbitrary code is a security hole, and an approval engine is the
last place to open one.

**Notifications run with elevated rights.** Deciding step one must not require
permission to create an activity for whoever handles step two. Without this, a
group step could not notify people the acting user has no rights over.

---

## Testing note

The engine's tests run against `res.partner` — a real model with chatter and
activities, rather than a fixture invented for the test. They cover process
resolution, step ordering, conditions, dynamic and group approvers, the
rejection cascade, and the activity lifecycle.

The mixin itself has no model inheriting it in these tests, because registering
a test-only model is fragile. Full mixin coverage arrives with the first
consumer module.

---

## Compatibility

- Odoo **19.0** Community and Enterprise
- Depends on `base`, `mail` and `hm_license` — no accounting, no HR, nothing
  country-specific
- Installation instructions: see `af_jalali/INSTALL.md`
