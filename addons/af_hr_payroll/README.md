# Afghanistan Payroll

Afghan wage withholding tax on a dated, editable scale — with salaries paid in
dollars assessed in afghani.

---

## Why this exists

Neither edition of Odoo has an Afghanistan payroll. Community has no payroll
engine at all, and Enterprise ships localizations for other countries. An
Afghan employer withholding tax from salaries has, until now, had a
spreadsheet.

This module is only the Afghan part. The engine underneath is `hm_payroll`.

---

## The scale is data, and it is dated

Tax law changes. A rate compiled into a Python file means every customer waits
for a release — and every historical payslip silently recomputes on the new
rate the moment somebody reopens it.

Here the brackets are an ordinary editable table with a start date:

| From | To | Fixed amount | Rate |
|---|---|---|---|
| 0 | 5,000 | 0 | 0% |
| 5,000 | 12,500 | 0 | 2% |
| 12,500 | 100,000 | 150 | 10% |
| 100,000 | *(open)* | 8,900 | 20% |

The **fixed amount** is the tax already due at the bracket's floor, so the rate
applies only to the part of the salary inside the bracket.

When rates change, close the scale with an end date and create a new one. A
payslip for last year stays taxed the way last year was taxed, because the
scale in force is chosen by the payslip's period.

> The preloaded figures are the long-standing statutory scale. Confirm them
> against current Afghanistan Revenue Department guidance before filing.

---

## The scale is validated as a scale

A gap between brackets leaves some salaries untaxed; an overlap taxes some
twice. Neither is visible until a payslip is checked by hand, so the module
refuses to save either.

- Each bracket must start exactly where the one below it ends.
- The lowest must start at zero, or salaries below it are never taxed.
- The highest must be open-ended (ceiling of zero), or a large enough salary
  falls off the top of the scale untaxed.
- A rate must be between 0 and 100 percent.

---

## Paid in dollars, taxed in afghani

Afghan tax is assessed in afghani. A salary paid in dollars is converted before
the scale is applied — at the rate agreed for that month, from
`af_dual_currency`, not at whatever the daily rate table happened to hold.

If no confirmed exchange period covers the payslip period, the module
**refuses to compute** and names the month to confirm. Picking a rate silently
would produce a tax figure nobody could reproduce.

---

## What it adds to payroll

- An income tax rule that reads the scale in force for the period.
- A salary structure using it, with the tax withheld as its own line.
- Advance recovery, so the instalment due is deducted and shown.

---

## Compatibility

- Odoo **19.0** Community and Enterprise
- Depends on `hm_payroll`, `af_hr`, `af_dual_currency` and `hm_license`
- Installation instructions: see `af_jalali/INSTALL.md`
