# Afghanistan — Accounting

Chart of accounts and taxes for Afghanistan.

---

## Why this exists

Odoo ships 225 fiscal localizations across its two editions. Afghanistan is not
among them. An Afghan company installing Odoo today builds a chart of accounts
from nothing and gets the tax treatment wrong on the way.

---

## Read this before you file anything

Afghan tax rates and thresholds change, and enforcement has varied. The rates
here reflect the long-standing Business Receipts Tax and withholding regime,
but **confirm them against current Afghanistan Revenue Department guidance
before filing**.

They are ordinary Odoo taxes. Edit them.

---

## The chart

Structured for Afghan businesses and NGOs rather than a generic chart
relabelled:

- **Dual AFN and USD cash and bank accounts**, because almost every
  organisation operating there runs both.
- **Staff advances** as a real account, since they are a standing feature of
  Afghan payroll — and `hm_payroll` recovers them through it.
- **Fixed-asset and accumulated-depreciation pairs**, already matched to what
  `hm_assets` expects.

There is no chart of accounts mandated for Afghanistan, so this is a sound
starting point rather than a legal requirement.

---

## Taxes

| Tax | Rates | Notes |
|---|---|---|
| Business Receipts Tax | 2%, 4%, 10% | the rate depends on the activity |
| Withholding — contractors | 2% licensed, 7% unlicensed | separate liability account |
| Withholding — rent | 10%, 15% | separate liability account |

### Why the withholding accounts are separate

Contractor and rent withholding are **filed separately**. Pooling them into one
payable makes the return a reconciliation exercise every month, instead of a
figure you can read off the trial balance.

---

## Installing it

Apply the chart template to the company from **Settings → Accounting** before
posting anything. A chart cannot be swapped underneath entries that already
exist.

Pairs naturally with `af_dual_currency` for the AFN/USD rate, and with
`hm_account_reports` for the statements Community does not have.

---

## Compatibility

- Odoo **19.0** Community and Enterprise
- Depends on `account` and `hm_license`
- Installation instructions: see `af_jalali/INSTALL.md`
