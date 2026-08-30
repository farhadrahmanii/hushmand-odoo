# Financial Reports

Trial balance, profit and loss, and balance sheet for Odoo Community.

---

## Why this exists

Community gives you journal items and a chart of accounts, and then stops.
Odoo's dynamic reports are Enterprise, so a Community user who has to file
accounts or hand something to an auditor has nothing to hand them.

---

## The three statements

### Trial Balance

Opening, movement and closing per account.

Income and expense accounts show **no opening balance**. They reset each
financial year, so a brought-forward figure there would be wrong — and it is
the mistake that makes a hand-built trial balance disagree with itself.

### Profit and Loss

Grouped into operating income, other income, cost of revenue, operating
expenses, depreciation and other expenses. Account types drive the grouping, so
a correctly typed chart needs no configuration.

### Balance Sheet

As at a date, including the **current period's result as equity**.

That result is not sitting in an account until the year is closed. Leave it out
and the sheet does not balance. And if the two sides disagree anyway, the
report says so in plain words rather than printing a total that looks
authoritative and is not.

---

## Filters

| Filter | Notes |
|---|---|
| Date range | any period, not only the fiscal year |
| Journal | leave empty for all |
| Company | one at a time |
| Analytic account | restrict to entries carrying it — the donor-report question |
| Posted entries only | on by default |

Turn posted-only off and the statement includes drafts — and prints
*“Includes draft entries. Not suitable for filing.”* across it. A management
figure and a filed figure are different things, and a report that does not say
which it is will eventually be filed.

---

## Printing

Ordinary QWeb, so the statements export to PDF like any other Odoo report and
can be styled by inheriting the templates.

Dates print through `af_jalali` if it is installed, so a filing prepared in
Kabul carries Hijri-Shamsi dates without a second report.

---

## Compatibility

- Odoo **19.0** Community and Enterprise
- Depends on `account` and `hm_license`
- Installation instructions: see `af_jalali/INSTALL.md`
