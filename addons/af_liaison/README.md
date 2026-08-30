# Afghanistan Liaison Documents

Visas, work permits, vehicle permits, weapon licences, membership cards and
airport CIP cards, with renewal reminders.

---

## Why this exists

An Afghan liaison office spends most of its time keeping six kinds of document
from lapsing. Losing a work permit deadline costs an employee their right to
work; losing a vehicle permit grounds a car.

---

## This module is deliberately thin

The tracking, the reminders and the renewal chain all come from **Expiring
Documents** (`hm_expiry_docs`), because a visa and a vehicle registration are
the same shape and did not need six separate models.

Six near-identical models would have been six copies of the same reminder
logic — and the sixth is the one where the bug would have lived.

---

## What is actually added here

| | |
|---|---|
| Six document types | ready configured, with sensible notice periods |
| A link to the employee | so an expiring permit shows on their record, and a warning appears on the employee form |
| The issuing province | which office issued it, for when you have to go back to them |
| The official reference | the maktoob or file number the issuing office quotes when you ring about it |

### The types

- Visa
- Work Permit
- Vehicle Permit
- Weapon Licence
- Membership Card
- Airport CIP Card

They are ordinary document types. Edit the notice periods, or add a seventh.

---

## Who gets reminded

The person named **responsible** — which in a liaison office is the officer who
has to do the renewing, not the employee whose permit it is.

That distinction is the difference between a reminder that produces action and
one that produces a forwarded email.

---

## On the employee

An employee with a document expiring or expired carries a flag, so the warning
appears where a manager is already looking rather than only in a list somebody
has to open.

---

## Compatibility

- Odoo **19.0** Community and Enterprise
- Depends on `hm_expiry_docs`, `hr`, `af_l10n_base` and `hm_license`
- Installation instructions: see `af_jalali/INSTALL.md`
