# Service Contracts

Recurring contracts that know when they are due, without billing anyone behind
your back.

---

## Why this exists

Odoo Subscriptions is Enterprise. A Community user with a maintenance
agreement, a security contract or an office lease has an invoice they remember
to raise, or forget to.

---

## Nothing is billed automatically

The daily job refreshes statuses, raises renewal reminders and flags what is
due — and stops there. It never raises an invoice on its own.

That is deliberate. Recurring billing that invoices silently is how a customer
receives a bill for a service that stopped three months ago, and how a supplier
relationship ends. Somebody presses **Create Invoice**, and what they get is a
**draft** to check before it is posted.

---

## What a contract knows

| | |
|---|---|
| Term | start and end date, or open-ended |
| Billing cycle | monthly, quarterly, every six months, yearly |
| Next invoice | when it is due |
| Annualised value | so monthly and yearly contracts can be compared |
| Direction | one you bill a customer for, or one a supplier bills you for |

Both directions are worth tracking; only the customer direction produces
invoices. Asking a supplier contract to invoice is refused with the reason.

---

## Renewals decided in time

A reminder is raised a **notice period** before the end date, so the decision to
renew or let it lapse is made before the date rather than discovered after it.

Contracts marked *Renews Automatically* extend themselves by one term when the
end date is reached, instead of expiring.

---

## States

```
Draft  →  Running  →  Expiring  →  Closed
              ↓
          Cancelled
```

Draft, running, closed and cancelled are set deliberately. **Expiring** is
derived from the end date by `_refresh_state`, which the daily job calls — it
cannot be a computed field, because the derivation has to read the current
state to know whether a contract is eligible at all.

### What is refused

| Action | Why |
|---|---|
| Cancel a contract that has been invoiced | close it instead, so the invoices keep their contract |
| Invoice a contract with no lines | there is nothing to bill |
| Invoice a supplier contract | it is billed *to* you |

---

## Lines

A line needs a description and a quantity greater than zero. A product is
optional — a contract line can describe a service that is not a catalogue
product, which is usually the case for the things contracts cover.

---

## Compatibility

- Odoo **19.0** Community and Enterprise
- Depends on `account` and `hm_license`
- Installation instructions: see `af_jalali/INSTALL.md`
