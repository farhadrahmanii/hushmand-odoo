# Dual Currency by Exchange Period

One agreed exchange rate per month, locked once reported, with totals shown in
both currencies.

---

## The problem this solves

Odoo keeps **one exchange rate per day** and converts using the nearest one.
That is right for a business marking to market daily.

It is wrong for an organisation that fixes a **single rate for the month** and
uses it for payroll, tax filings and every document issued in that period.
Two things are missing from the plain rate table:

1. Nothing groups a month's documents to one agreed rate.
2. Nothing stops someone editing a historical rate — silently changing
   figures that have already been reported to the ministry.

Both matter. The second one is an audit problem, not an inconvenience.

---

## How it works

Define a period, set the rate, confirm it.

| State | Meaning |
|---|---|
| **Draft** | A proposal. Ignored by conversions — an unconfirmed rate is not something to report on |
| **Confirmed** | Published to Odoo. Every document in the period uses it |
| **Closed** | Locked. The rate cannot be edited, and the period cannot be deleted |

Reopening a closed period is possible but deliberate, and warns you that
anything already reported will no longer match.

### It feeds Odoo rather than replacing it

Confirming a period writes an ordinary `res.currency.rate`. Invoices,
accounting, reports and every other module keep working exactly as before.
This module adds governance **on top of** Odoo's mechanism, so nothing has to
know it exists.

That is deliberate. A parallel rate system would drift out of sync with the
one Odoo actually uses for its own accounting.

---

## A missing rate returns zero, not a guess

If no confirmed period covers a date, conversion returns **zero**.

It would have been easy to fall back to Odoo's daily rate. That would produce
a plausible-looking number that nobody agreed to, on a document that may end
up in a tax filing. A zero is obvious and gets fixed. A wrong number gets
filed.

---

## Setting it up

1. **Settings → General Settings → Second Currency.** Choose AFN. The afghani
   ships with Odoo but switched off; this module activates it.
2. **Invoicing → Configuration → Exchange Periods.** Create a period, set the
   rate, confirm.

The rate is *units of the second currency for one unit of the company
currency*: with the company in USD and a rate of 70, one dollar is 70 afghani.
The form shows the inverse alongside it so a mistyped rate is obvious.

To set up a year at once:

```python
env['af.exchange.period'].create_monthly_periods(2027, rate=72.0)
```

That creates twelve draft periods; correct each rate before confirming it.

---

## On documents

Invoices and bills show the total in the second currency, together with **the
period that produced it** — so any figure can be traced back to an agreed
rate rather than being an unexplained number on a page.

---

## For other modules

```python
Period = self.env['af.exchange.period']

amount, period = Period._convert(1000.0, invoice_date)
# amount is zero and period empty when no confirmed period covers the date

period = Period._period_for(date)          # the governing period, or empty
```

The Afghan payroll module uses this to put gross, tax and net on a payslip in
both currencies at the rate agreed for that month.

---

## Beyond Afghanistan

Nothing here is Afghanistan-specific. Any organisation that has to report in a
second currency at an agreed rate rather than a floating one can use it —
which is most organisations operating under a currency control regime, and
most NGOs reporting to a donor in a different currency from the one they spend.

---

## Compatibility

- Odoo **19.0** Community and Enterprise
- Depends on `base`, `base_setup`, `account` (Invoicing, free in Community)
  and `hm_license`
- Installation instructions: see `af_jalali/INSTALL.md`
