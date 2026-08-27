# Purchase Requests

The step before the quotation: a department asks, and the request is approved
on its own merits before anyone talks to a supplier.

---

## Why this exists

Odoo starts at the **request for quotation** — by which point someone has
already decided what to buy and from whom. Most organisations have a step
before that, and Odoo Community has nothing for it.

A purchase request carries the items, an estimated cost, a budget line and a
written justification. Approvers read the justification first, so it is a real
field rather than a note at the bottom.

---

## Approval routing is configuration, not code

Routing comes from **Approval Workflows** (`hm_approvals`), so who signs off
and in what order is set up by the customer, not written by a developer.

Because steps can be conditional, one process handles both sizes of request:

| Request | Route |
|---|---|
| Office chairs, 450 | Manager |
| Vehicles, 5,000 | Manager, then Director |

No second process to keep in step with the first. The condition lives on the
Director step: *only when `amount_total` is greater than 1000*.

Approvers can also be resolved from the request itself — the requester's
manager, the owner of the budget line — so the process survives people
changing roles.

---

## The flow

```
Draft  →  Waiting Approval  →  Approved  →  Ordered
                  ↓
              Rejected  →  (reset to draft, resubmit)
```

Resetting a rejected request to draft **clears the old approval**, so
resubmitting starts a fresh chain rather than reusing decisions that were made
about a different version of the request.

An approved request becomes a quotation in one click. Items, quantities,
prices and the budget line carry across, and the purchase order keeps a link
back to the request it came from.

---

## Products are optional

A line needs a description; a product is optional. People usually request
things that are not in the catalogue yet — that is often *why* they are
requesting them. Forcing a product first would mean creating catalogue entries
for things nobody has agreed to buy.

If a product is chosen, the unit and cost fill in from it.

---

## Who sees what

| | |
|---|---|
| Requesters | Their own requests, plus anything they have been asked to approve |
| Purchasing managers | Everything |

Approvers also reach the request through their normal Odoo activity.

---

## Compatibility

- Odoo **19.0** Community and Enterprise
- Depends on `purchase` and `hm_approvals`
- Installation instructions: see `af_jalali/INSTALL.md`
