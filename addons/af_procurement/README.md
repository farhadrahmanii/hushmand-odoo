# Afghanistan Procurement

The comparative form: which suppliers were asked, what each quoted, and why the
chosen one was chosen.

---

## Why this exists

The chain an Afghan office runs is a purchase request, then quotations compared
on a comparative form, then a purchase order, then a goods received note. Odoo
has the middle of that. What it has no concept of at all is the **comparative
form**.

That sheet is the audit trail. A donor or an auditor asking *“why this
supplier”* is asking for exactly this document, and in most offices it lives in
a folder rather than in the system — which is why it is so often missing when
somebody finally asks.

---

## Two rules, and both exist because of that question

### A comparison needs at least two quotations

With one, nothing has been compared, and calling the sheet a comparison would
be a lie on the file.

### Choosing anyone other than the cheapest requires a written reason

Not optionally, and not later. The form will not complete without it.

That sentence is trivial to write on the day and close to impossible to
reconstruct a year afterwards — which is when it gets asked for.

The fact that the chosen quotation was not the lowest is **stored**, not
computed, so the search filter can find these forms. That flag is what an
auditor filters on, and a filter that cannot be searched is a filter nobody
uses.

---

## What each quotation records

| Field | Why it is on the sheet |
|---|---|
| Supplier and amount | the comparison itself |
| Quotation number and date | the supplier's own reference, so the paper can be found again |
| Delivery in days | often the reason a dearer quotation wins |
| Warranty in months | the other common reason |
| Payment terms | a cheaper price on worse terms is not cheaper |

The lowest quotation is marked automatically. It is not necessarily the one
chosen — that is the whole point of the sheet.

---

## The flow

```
Purchase request (submitted)
        ↓
Comparative form  →  quotations  →  choose  →  Complete
        ↓
Supplier set on the request  →  Quotation  →  Purchase order
```

Completing the form sets the supplier on the purchase request, which then
becomes an ordinary Odoo quotation.

A completed comparison cannot be cancelled. It is part of the record of how the
supplier was chosen.

---

## Compatibility

- Odoo **19.0** Community and Enterprise
- Depends on `hm_purchase_request` and `hm_license`, which bring `purchase` and
  the approval engine with them
- Installation instructions: see `af_jalali/INSTALL.md`
