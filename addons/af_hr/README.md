# Afghanistan HR

Afghan employee records need things Odoo's HR has no place for. This module
adds them where they belong rather than bolting them onto the side.

---

## What it adds

| | |
|---|---|
| **Father's and grandfather's names** | Afghan names carry no inherited surname |
| **Tazkira** | Volume, page and register for paper; national ID for electronic |
| **TIN** | Required on the payroll return |
| **Addresses** | District and village, current *and* permanent, separately |
| **Disciplinary actions** | Nothing comparable exists in either Odoo edition |
| **ID cards** | Printed from the employee record |

---

## Why the fields live on the version

Odoo 19 replaced contracts with **versions**: `hr.employee` delegates to
`hr.version`, and versions form a dated timeline.

Putting Afghan identity and address fields there means they read and write
from the employee exactly as if they were on it — and a corrected name or a
change of address becomes **history** rather than erasing what the record said
before. On an employment file that is the difference between a record you can
defend and one you cannot.

It also means this module does **not** ship an amendment-history model. Odoo
now does that natively, and a parallel history would only drift out of step
with it.

---

## Names

There is no inherited surname in Afghan naming. A person is identified by
their own name plus their father's and grandfather's, and every official
document is issued that way. `af_full_identity` composes the string that goes
on a letter:

```
Ahmad Shah, s/o Mohammad Nabi, g/o Abdul Ghani
```

## Tazkira

A **paper** tazkira is identified by three numbers *together* — volume (jild),
page (safha) and registration entry (sabt). An **electronic** one has a
national identity number instead.

Both are in circulation, so the module records both rather than forcing one
into the other's shape. `af_tazkira_reference` renders the paper form the way
a clerk reads it:

```
Volume 12, Page 340, Register 56
```

## Addresses

Odoo's private address stops at the province. Afghan records go two levels
further, and distinguish where someone **lives now** from where they are
**from** — the address on the tazkira. Both are recorded, both down to
village level, using the geography from `af_l10n_base`.

---

## Disciplinary actions

Verbal warning through to termination, at **Employees → Disciplinary
Actions**.

| State | Meaning |
|---|---|
| Draft | Being prepared |
| Issued | Given to the employee |
| **Acknowledged** | The employee confirmed receipt — recorded separately, with its own date |
| Closed | Concluded |
| Cancelled | Withdrawn before conclusion |

Issue and acknowledgement are deliberately separate. If an action is ever
challenged, whether the employee actually saw it is the part that matters, and
"we sent it" is not the same claim as "they received it".

A closed action cannot be cancelled — record a new action instead, so the
history stays intact.

---

## Compatibility

- Odoo **19.0** Community and Enterprise
- Depends on `hr` and `af_l10n_base`
- Pair with `af_jalali` for Jalali dates throughout
- Installation instructions: see `af_jalali/INSTALL.md`
