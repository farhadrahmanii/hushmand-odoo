# Hushmand Odoo Addons

Proprietary Odoo modules for Afghanistan and for the gaps in Odoo Community.
Sold directly; see [`LICENSE.md`](LICENSE.md).

Target: **Odoo 19.0**. Plan: `E:\web\MyERP\docs\odoo-migration\ODOO_MODULE_PLAN.md`.

---

## The licensing rule

**Never add a dependency on an AGPL-3 module.**

Odoo Community core is LGPL-3, which permits proprietary addons. Most OCA
modules are AGPL-3, and depending on one would force these modules to AGPL too
— meaning any customer could legally redistribute them for free. Check before
you add anything:

```bash
grep -H '"license"' /path/to/candidate/__manifest__.py
```

Anything reporting `AGPL-3` is reference material, not a dependency. Read it,
then re-implement what you need on core.

---

## Layout

```
addons/<module>/        one module per directory
  core/                 Tier 0 -- pure Python, no Odoo imports
  models/               Tier 1 -- ORM, stable APIs only
  views/ static/        Tier 2 -- version-sensitive UI
  tests/
docker/                 local stack configuration
tools/                  developer scripts
```

### The three tiers

A module cannot install across Odoo versions — the manifest version is
series-pinned, view tags change, OWL churns. What it *can* do is confine the
damage:

| Tier | Content | On a new Odoo release |
|------|---------|------------------------|
| **0** | Business logic, pure Python, no Odoo imports | Unchanged, always |
| **1** | Models using long-stable ORM APIs | Usually unchanged |
| **2** | Views, OWL components, assets | Expect to touch this |

Porting means branching (`19.0` → `20.0`) and reviewing Tier 2. Keep Tier 0
free of Odoo imports and that promise holds.

---

## Running locally

```bash
docker compose up -d
docker compose exec odoo odoo -d dev -i af_jalali --stop-after-init
```

Then open <http://localhost:8069>.

Tier 0 tests need no Odoo and no database:

```bash
python tools/run_core_tests.py
```

Full test suite, inside the container:

```bash
docker compose exec odoo odoo -d dev -i af_jalali --test-enable --stop-after-init
```

Verify the Python and JavaScript conversions still agree (they must, or a date
printed on a report will differ from the same date on screen):

```bash
python tools/verify_js_python_parity.py
```

---

## Modules

All 20 install and pass their tests on Odoo 19 in CI (497 tests).

| Module | Line | What it does | Tests |
|--------|------|--------------|-------|
| `af_correspondence` | Afghanistan | Incoming and outgoing official letters, numbered in order | 17 |
| `af_dual_currency` | Afghanistan | One agreed AFN/USD rate per month, locked once reported, with totals shown in both currencies | 29 |
| `af_hr` | Afghanistan | Tazkira, father and grandfather names, Afghan addresses, ID cards and disciplinary actions | 23 |
| `af_hr_payroll` | Afghanistan | Afghan wage withholding tax on a dated, editable scale, with salaries paid in dollars taxed in afghani | 36 |
| `af_jalali` | Afghanistan | Hijri-Shamsi dates across Odoo, with Afghan and Iranian month names | 62 |
| `af_l10n_account` | Afghanistan | Chart of accounts and taxes for Afghanistan | 15 |
| `af_l10n_base` | Afghanistan | Afghan provinces and districts, tazkira and TIN fields, trilingual and ready to use | 31 |
| `af_liaison` | Afghanistan | Visas, work permits, vehicle permits, weapon licences, membership and CIP cards, with renewal reminders | 10 |
| `af_procurement` | Afghanistan | The comparative form: which suppliers were asked, what each quoted, and why the chosen one was chosen | 18 |
| `af_zakat` | Afghanistan | Collect, hold and distribute zakat, with a record that reconciles | 23 |
| `hm_account_reports` | Horizontal | Trial balance, profit and loss, and balance sheet for Odoo Community | 17 |
| `hm_approvals` | Horizontal | Route any document through a configurable multi-step approval chain, with conditions and dynamic approvers | 28 |
| `hm_assets` | Horizontal | Asset register and depreciation for Odoo Community | 26 |
| `hm_contracts` | Horizontal | Recurring contracts that know when they are due, without billing anyone behind your back | 27 |
| `hm_expiry_docs` | Horizontal | Track anything with an expiry date, and be reminded before it lapses | 24 |
| `hm_frontdesk` | Horizontal | Visitor register: who is in the building, and who they came to see | 21 |
| `hm_license` | Horizontal | Offline licence verification for commercial Odoo modules | 27 |
| `hm_payroll` | Horizontal | Salary structures, rules and payslips for Odoo Community | 20 |
| `hm_purchase_request` | Horizontal | The step before the quotation: a department asks, and the request is approved on its own merits | 22 |
| `hm_roster` | Horizontal | Schedule guards, drivers or a reception desk, and be told when the roster is broken | 21 |

`af_*` modules are Afghanistan and Persian-market localization.
`hm_*` modules fill Odoo Community gaps and sell worldwide.

---

## Licence enforcement

Every paid module depends on `hm_license` and gates its main document model
behind `hm.license.gate`. The gate blocks `create` and `write`. It does not
block reading, printing, exporting or deleting: an unlicensed database goes
read-only in the modules it has not paid for, and every payslip, contract and
report the customer already produced stays visible forever. Holding a
customer's own data hostage turns a late renewal into a dispute; refusing new
work is enough pressure on its own.

A lapsed licence keeps working for a further **30 days** (`GRACE_DAYS`), with
a countdown in the systray throughout. Payroll must not stop on the morning a
renewal invoice happens to be late.

Four modules carry no gate of their own, each for a reason recorded in
`UNGATED` in `tools/build_release.py`: `hm_license` is the licence module,
`af_jalali` and `af_l10n_account` ship only widgets and data with no documents
to gate, and `af_liaison` gates through `hm_expiry_docs`, whose documents it
extends. A test reads that list rather than repeating it, so the packaging
guard and the test cannot drift apart.

### Arming it — the one manual step before any sale

The gate enforces nothing until a real vendor public key replaces the
placeholder in `addons/hm_license/models/hm_license.py`. That is deliberate:
it keeps the whole catalogue testable without a signed licence. It also means
a forgotten key produces modules that install, run, sell — and check nothing.
A failure that is invisible because everything appears to work.

```bash
python tools/issue_license.py --generate-keys
```

Put the public half into `VENDOR_PUBLIC_KEY`. **Keep the private half off this
repository and off every customer machine** — it is the only thing preventing
anyone from minting their own licences. `tools/build_release.py` refuses to
package anything while the placeholder is still in place, and refuses any
module that inherits no gate.

---

## Before releasing any module

- [x] Installs on a clean database with no other addon present — the CI
      Odoo job builds one from scratch every push
- [x] `--test-enable` passes — CI greps the log for ERROR/CRITICAL, because
      Odoo exits 0 even when tests fail
- [x] `static/description/icon.png` (140×140) — generated by
      `python tools/generate_icons.py`, and CI fails if one is missing or a
      `web_icon` points at a file that is not there
- [ ] `banner.png` drawn and the `images` key re-enabled in the manifest
- [x] Demo data loads and shows something meaningful — CI loads it, because
      `--without-demo` is deliberately not passed
- [ ] Translations exported and `fa` / `ps` filled in
- [ ] RTL checked visually in Dari
- [ ] `static/description/index.html` written, with screenshots
- [ ] Version bumped, changelog updated
- [ ] Licence header on every file
- [x] Gated behind `hm.license.gate`, or listed in `UNGATED` with a reason —
      CI fails if a module checks no licence, and packaging refuses it
- [ ] `VENDOR_PUBLIC_KEY` set to a real key — until then the gate is inert,
      and `tools/build_release.py` will not package anything
- [x] No AGPL dependency anywhere in the tree — CI fails on the string
