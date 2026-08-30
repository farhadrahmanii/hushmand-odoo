# Fixed Assets

An asset register and depreciation schedule for Odoo Community.

---

## Why this exists

Odoo's asset management is Enterprise. A Community user who buys a vehicle has
a bill and nothing else: no register, no depreciation, and a balance sheet that
overstates what the company owns for the rest of the asset's life.

---

## The schedule

| Option | Choices |
|---|---|
| Method | straight line, reducing balance |
| Frequency | monthly, quarterly, yearly |
| First period | prorated from the in-service date, or a full period |
| Salvage value | never depreciated past |

Depreciation runs from the **in-service date**, not the invoice date. An asset
bought in December and put to work in February is not depreciated for the two
months it sat in a store.

### Reducing balance

The reducing factor is the share of the remaining value written off each
period, between 0 and 1. A factor of 0.25 with an annual frequency writes off a
quarter of what is left each year, and the schedule stops at the salvage value.

---

## Nothing posts by itself

The schedule is a **forecast** until somebody confirms a period. There is no
cron quietly writing entries into a month that has been closed.

```
Draft  →  Running  →  Closed
             ↓
        post period 1, 2, 3 … as each falls due
```

- Recomputing leaves posted periods untouched and reschedules only what is left.
- A posted period cannot be edited or deleted. To change it you reverse its
  journal entry, so the ledger keeps a record of both.
- Cancelling an asset with posted depreciation is refused — close it instead,
  so the entries stay.

---

## Categories carry the defaults

The method, the number of periods and the three accounts live on the category,
so recording a vehicle takes one screen rather than four decisions.

They are **copied** onto a new asset, not linked. Changing a category later
does not reach back and alter assets that already exist, which is what you want
and not what a related field would have done.

### The three accounts

| Account | Role |
|---|---|
| Asset | where the asset sits on the balance sheet |
| Depreciation expense | debited each period |
| Accumulated depreciation | credited each period — usually a negative asset account |

`af_l10n_account` ships matching pairs if you want them.

---

## What you can see

- Depreciated so far, and the remaining book value, on the asset itself.
- **Periods due now** — the filter for the month-end run.
- Assets with unposted periods flagged, so one that has quietly stopped being
  depreciated is visible rather than merely absent.

---

## Compatibility

- Odoo **19.0** Community and Enterprise
- Depends on `account` and `hm_license`
- Installation instructions: see `af_jalali/INSTALL.md`
