# Pricing the catalogue

**The numbers below are a starting point, not a decision.** They are grounded
in what the market charges and in what each module costs to deliver, but only
you know your cost base, your pipeline, and what an Afghan ministry will
actually sign. Change them.

What this document is really for is the structural problem in the middle
section, which is not a matter of opinion and would cost real money to
discover after the first contract.

---

## 1. The problem: dependencies decide what you are selling

A licence names modules. The gate asks for a licence covering the module that
**declares** the record being written — not the module the customer thought
they bought.

`hm.payslip` is declared in `hm_payroll`. So:

> A customer who buys **`af_hr_payroll`** and holds a licence naming only
> `af_hr_payroll` is refused the first payslip they create.

`tools/issue_license.py` now expands every licence to its closure
automatically, so this cannot be got wrong by hand. But it means the
commercial unit is the closure, not the module:

| Sold | Licence must actually cover | Modules |
|---|---|---|
| `af_hr_payroll` | + `hm_payroll`, `af_hr`, `af_dual_currency`, `af_l10n_base`, `hm_license` | 6 |
| `af_procurement` | + `hm_purchase_request`, `hm_approvals`, `hm_license` | 4 |
| `af_liaison` | + `hm_expiry_docs`, `af_l10n_base`, `hm_license` | 3 |

**You cannot sell the Afghan payroll without licensing the payroll engine.**
That is not a bug to fix — `af_hr_payroll` is a thin layer of Afghan tax law
on top of `hm_payroll` and was designed that way. It is a fact to price.

### What it does to the suites

```bash
python tools/build_release.py --suite afghanistan --plan
```

| Suite | Sold as | Resolves to | Line B modules given away |
|---|---|---|---|
| `hr` | 5 | 9 | — (already mostly Line B) |
| `finance` | 6 | 8 | — |
| `office` | 7 | 9 | — |
| **`afghanistan`** | **10** | **15** | **`hm_approvals`, `hm_payroll`, `hm_purchase_request`, `hm_expiry_docs`** |
| `complete` | 21 | 21 | — |

The Afghanistan suite is the problem. Priced as "the Afghan localization" it
hands over four of the horizontal modules — the ones whose market is every
Odoo Community user on earth, not just Afghanistan.

**Recommendation: do not sell `afghanistan` as a discount tier.** Price it at
or near the complete catalogue, or drop it and sell `complete` instead. The
five modules it excludes (`hm_account_reports`, `hm_assets`, `hm_contracts`,
`hm_frontdesk`, `hm_roster`) are not worth the discount it implies.

---

## 2. What the market charges

Third-party Odoo App Store modules sell for roughly **USD 50–500 each**, or
**USD 200–800 one-off**, with annual maintenance typically **10–20%** of the
purchase price. Odoo's own apps are not priced individually; they come with a
per-user subscription (USD 25–32/user/month on the Custom tier).

Two things follow.

**You are not competing with Odoo's per-user price.** A Community customer has
already decided not to pay it. You are competing with the spreadsheet they use
instead, and with the cost of a developer building it for them once.

**The App Store range is for single-purpose modules.** `hm_payroll` is a
payroll engine with 42 tests and 2,200 lines; it is not a $50 field-adder.
Pricing at the top of the range is defensible, and the bottom of it is not.

---

## 3. What each module costs to deliver

Not a price. A sanity check that the prices are ordered sensibly.

| Module | Python lines | Tests | Replaces |
|---|---|---|---|
| `hm_payroll` | 2,201 | 42 | nothing in Community |
| `af_jalali` | 1,444 | 62 | nothing free that is correct |
| `hm_approvals` | 1,352 | 28 | nothing in Community |
| `hm_license` | 1,272 | 54 | — (your own infrastructure) |
| `hm_assets` | 1,013 | 26 | Enterprise |
| `hm_timesheet` | 908 | 30 | Enterprise (`timesheet_grid`) |
| `hm_contracts` | 859 | 27 | Enterprise (Subscriptions) |
| `hm_expiry_docs` | 858 | 36 | nothing anywhere |
| `af_dual_currency` | 829 | 29 | nothing anywhere |
| `af_zakat` | 747 | 23 | nothing anywhere |
| `af_hr` | 730 | 23 | nothing anywhere |
| `af_hr_payroll` | 716 | 36 | nothing anywhere |
| `hm_account_reports` | 709 | 17 | Enterprise |
| `hm_purchase_request` | 693 | 22 | nothing in Community |
| `af_l10n_base` | 638 | 31 | nothing anywhere |
| `hm_roster` | 631 | 21 | Enterprise (Planning) |
| `af_procurement` | 598 | 18 | nothing anywhere |
| `hm_frontdesk` | 485 | 21 | Enterprise (Frontdesk) |
| `af_correspondence` | 477 | 17 | nothing anywhere |
| `af_l10n_account` | 296 | 15 | nothing anywhere |
| `af_liaison` | 291 | 10 | nothing anywhere |

The "replaces" column matters more than the line count. A module replacing an
Enterprise app is priced against what Enterprise costs that customer. A module
replacing *nothing* — `af_zakat`, `af_dual_currency`, the correspondence
register — has no comparison at all, which cuts both ways: no price anchor,
and no competitor.

---

## 4. A structure to start from

**Per-module, one-off licence**, banded rather than individually priced.
Banding stops a customer negotiating each module and stops you maintaining
twenty-one prices.

| Band | Modules | Suggested one-off |
|---|---|---|
| **A — engines** | `hm_payroll`, `hm_approvals`, `af_jalali` | USD 600 |
| **B — Enterprise replacements** | `hm_assets`, `hm_timesheet`, `hm_contracts`, `hm_account_reports`, `hm_roster`, `hm_frontdesk` | USD 400 |
| **C — Afghan specifics** | `af_hr`, `af_hr_payroll`, `af_dual_currency`, `af_zakat`, `af_procurement`, `af_correspondence`, `af_l10n_base`, `af_l10n_account`, `af_liaison` | USD 300 |
| **D — supporting** | `hm_expiry_docs`, `hm_purchase_request` | USD 300 |
| — | `hm_license` | included, never sold alone |

### Suites, at a discount that reflects the closure

| Suite | Sum of parts | Suggested | Discount |
|---|---|---|---|
| `hr` | ~2,500 | 1,800 | 28% |
| `finance` | ~2,100 | 1,500 | 29% |
| `office` | ~2,300 | 1,600 | 30% |
| `afghanistan` | ~4,400 | **3,600** | 18% — deliberately shallow, see §1 |
| `complete` | ~7,800 | 5,000 | 36% |

### Annual maintenance

**20% of the purchase price**, optional, covering fixes, Odoo point-release
compatibility, and support within the SLA. At the top of the market range
because you are a single supplier rather than a marketplace, and because the
Odoo-version treadmill is the real cost you are funding.

**Do not make it mandatory in year one.** A customer who has never bought from
you will not sign a recurring commitment; sell the licence, deliver, then sell
the renewal on the strength of having delivered.

---

## 5. One-off or subscription

The plan left this open. The recommendation is **one-off licence plus optional
annual maintenance**, for one reason:

> A subscription funds version upgrades. A one-off does not, and Odoo ships a
> new major version every year.

But an Afghan ministry or NGO buying software has a procurement process built
around a purchase, not a subscription, and the annual renewal is the thing
most likely to fail their process rather than yours. Sell the way the customer
can actually buy, and price the first licence high enough that carrying one
version upgrade unpaid is survivable.

Revisit once you have five customers and know how many of them renewed.

---

## 6. What is still missing before you can quote

- **A support SLA in writing.** See [`SUPPORT-SLA.md`](SUPPORT-SLA.md).
  Without one, every customer assumes unlimited free support and is right to.
- **A decision on discounting for the first two or three customers.** Whatever
  you decide, decide it now: a discount given ad hoc to the first buyer sets
  your price for every buyer who talks to them.
- **Whether `af_l10n_base` is ever sold alone.** It is a dependency of six
  other modules and carries the province and district data everything else
  relies on. Consider bundling it free with any `af_*` purchase — the goodwill
  costs you nothing you would otherwise have sold.

---

## Sources

Market figures from published 2026 Odoo pricing analyses:

- [Odoo Pricing 2026: True Cost, Not Promo — ERP Research](https://www.erpresearch.com/pricing/odoo)
- [Odoo Pricing: Implementation Cost and Pricing Details 2026 — Whizzbridge](https://www.whizzbridge.com/blog/odoo-pricing)
- [Odoo Pricing 2026: Transparent Breakdown — Octura Solutions](https://octurasolutions.com/resources/odoo-pricing-2026-complete-transparent-breakdown-us-canada)
