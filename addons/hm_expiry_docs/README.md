# Expiring Documents

Track anything with an expiry date, and be reminded before it lapses.

---

## Why this exists

Every organisation tracks things that expire — licences, permits, visas,
insurance, vehicle registrations, professional certifications — and most track
them in a spreadsheet that nobody opens until something has already lapsed.

---

## One model, not six

A work permit and a vehicle registration are the same shape: a number, a
holder, an issue date, an expiry date and somebody responsible. Six
near-identical models would have been six places to fix the same bug.

The **document type** carries the differences:

| On the type | Effect |
|---|---|
| Usual validity, in months | suggests the expiry date; always overridable |
| Remind before, in days | how much notice the responsible person gets |
| Number required | a passport has a number; a signed undertaking may not |

---

## Reminders that reach a person

Whoever is named **responsible** gets an ordinary Odoo activity before the
document lapses — so it appears where they already work, not in a report they
have to remember to open.

Once, not every morning. A reminder that repeats daily is a reminder people
learn to ignore, and the flag that records it was raised is what stops the
repeat.

The responsible person is not necessarily the holder. For a liaison office it
is the officer who does the renewing, not the employee whose permit it is.

---

## Renewal keeps the history

Renewing opens a replacement carrying the details over, closes the old document
and links the two.

```
Work permit 2024  →  renewed by  →  Work permit 2025  →  …
```

The chain of a licence over ten years stays intact and searchable, rather than
being one record overwritten nine times.

---

## Status is stored, not computed

| Status | Set by |
|---|---|
| Valid, Expiring, Expired | the dates, refreshed by the daily job |
| Renewed | by hand, when a replacement is issued |
| Cancelled | by hand, when a document is withdrawn |

The status depends on today. A computed field is calculated when the record is
read, which means it cannot be searched or grouped — and a list of everything
expiring this month is the entire reason for the module. So it is stored, and
the daily job keeps it honest.

Renewed and cancelled override the dates and stop the reminders.

---

## Extending it

`af_liaison` is the worked example: six Afghan document types, a link to the
employee, the issuing province and the official reference — and not one line of
reminder logic, because it inherits all of it.

---

## Compatibility

- Odoo **19.0** Community and Enterprise
- Depends on `mail` and `hm_license`
- Installation instructions: see `af_jalali/INSTALL.md`
