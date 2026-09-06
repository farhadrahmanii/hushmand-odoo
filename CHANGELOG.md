# Changelog

Every module carries its own `version` in `__manifest__.py`, in Odoo's format:

```
19.0 . 1 . 0 . 0
 │     │   │   └── patch — a fix, no new fields, no migration
 │     │   └────── minor — new fields or features, installs over the previous
 │     └────────── major — a change a customer has to be told about
 └──────────────── the Odoo series the module is built for
```

Porting to a new Odoo series means branching (`19.0` → `20.0`), not bumping the
first number in place. A customer on Odoo 19 must be able to keep receiving
fixes after Odoo 20 exists.

Bundles are named for the catalogue version, which moves when any module in
them does.

---

## 19.0.1.0.0

The first sellable build of the catalogue. Twenty-one modules, two product
lines, and archives that build.

**Nothing has been sold yet.** The code is complete and packageable: the vendor
signing key exists, the gate is armed, and `tools/build_release.py` produces
twenty-one module archives and five suite bundles with checksums. What remains
before a customer sees it is commercial rather than technical — pricing, a
support SLA, and a native-speaker review of the Dari.

### Line A — Afghanistan and the Persian-calendar market

| Module | What it does |
|---|---|
| `af_jalali` | Hijri-Shamsi dates across Odoo, Afghan and Iranian month names, Pashto included |
| `af_l10n_base` | 34 provinces, 546 districts, tazkira and TIN, trilingual |
| `af_l10n_account` | Afghan chart of accounts, Business Receipts Tax, withholding |
| `af_dual_currency` | One agreed AFN/USD rate per period, locked once reported |
| `af_hr` | Afghan names, the tazkira as it really is, disciplinary actions |
| `af_hr_payroll` | Afghan wage withholding on a dated scale; dollars taxed in afghani |
| `af_procurement` | The comparative form — why this supplier, on the file |
| `af_correspondence` | The maktoob register, two numbered series |
| `af_liaison` | Visas, work permits, weapon licences, CIP cards |
| `af_zakat` | Collect, hold and distribute zakat, reconciled |

### Line B — horizontal, for every Odoo Community user

| Module | Fills the gap left by |
|---|---|
| `hm_approvals` | nothing in Community; Enterprise Approvals models the wrong thing |
| `hm_payroll` | no payroll engine in Community at all |
| `hm_purchase_request` | Odoo starts at the RFQ |
| `hm_account_reports` | dynamic reports are Enterprise |
| `hm_assets` | asset management is Enterprise |
| `hm_contracts` | Subscriptions is Enterprise |
| `hm_expiry_docs` | nothing tracks expiry generically |
| `hm_frontdesk` | Frontdesk is Enterprise |
| `hm_roster` | Planning is Enterprise |
| `hm_license` | licence enforcement, for this catalogue and resellable |
| `hm_timesheet` | Community records hours; it has no week to submit or approve |

### Also in this build

- **Licence enforcement.** `hm.license.gate` on every paid module's main
  document model. Blocks new work when unlicensed; never blocks reading,
  printing or exporting what the customer already produced. Thirty-day grace
  period after expiry, with a countdown in the systray throughout.
- **Dari (`fa_AF`) translation** of all 2,051 terms — **a first draft, not
  reviewed by a native speaker.** Do not ship it to a customer as finished.
- **Translation templates** for all twenty-one modules, with CI failing if a
  source string changes and the template is not regenerated.
- **A listing page, a README, an icon, a banner and a screenshot** for
  every module. The screenshot is taken from a real Odoo by CI, which
  also fails if any screen stops rendering.
- **Dependency-resolving packaging.** `tools/build_release.py` computes what
  else a customer needs, bundles suites, and writes SHA-256 checksums.

### Known gaps

- Pashto (`ps_AF`) is not translated. The pipeline and
  `docs/TRANSLATOR-BRIEF.md` are ready; no translator has been engaged.
- The Dari is a first draft by an AI and has not been reviewed by a native
  speaker.
- The licence gate stands down under `--test-enable`, so the catalogue's own
  546 tests need no licence. Named here because it is a real hole, if a narrow
  one.
- Villages ship as structure with no data, on purpose: no reliable public
  dataset of Afghan villages exists.
- Afghan tax rates are the long-standing statutory ones and are editable
  tables. Confirm against current Afghanistan Revenue Department guidance
  before filing.
