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

All 20 install and pass their tests on Odoo 19 in CI (516 tests).

| Module | Line | What it does | Tests |
|--------|------|--------------|-------|
| `af_correspondence` | Afghanistan | Incoming and outgoing official letters, numbered in order | 25 |
| `af_dual_currency` | Afghanistan | One agreed AFN/USD rate per month, locked once reported, with totals shown in both currencies | 33 |
| `af_hr` | Afghanistan | Tazkira, father and grandfather names, Afghan addresses, ID cards and disciplinary actions | 29 |
| `af_hr_payroll` | Afghanistan | Afghan wage withholding tax on a dated, editable scale, with salaries paid in dollars taxed in afghani | 46 |
| `af_jalali` | Afghanistan | Hijri-Shamsi dates across Odoo, with Afghan and Iranian month names | 25 |
| `af_l10n_account` | Afghanistan | Chart of accounts and taxes for Afghanistan | 17 |
| `af_l10n_base` | Afghanistan | Afghan provinces and districts, tazkira and TIN fields, trilingual and ready to use | 41 |
| `af_liaison` | Afghanistan | Visas, work permits, vehicle permits, weapon licences, membership and CIP cards, with renewal reminders | 12 |
| `af_procurement` | Afghanistan | The comparative form: which suppliers were asked, what each quoted, and why the chosen one was chosen | 24 |
| `af_zakat` | Afghanistan | Collect, hold and distribute zakat, with a record that reconciles | 33 |
| `hm_account_reports` | Horizontal | Trial balance, profit and loss, and balance sheet for Odoo Community | 19 |
| `hm_approvals` | Horizontal | Route any document through a configurable multi-step approval chain, with conditions and dynamic approvers | 40 |
| `hm_assets` | Horizontal | Asset register and depreciation for Odoo Community | 28 |
| `hm_contracts` | Horizontal | Recurring contracts that know when they are due, without billing anyone behind your back | 37 |
| `hm_expiry_docs` | Horizontal | Track anything with an expiry date, and be reminded before it lapses | 48 |
| `hm_frontdesk` | Horizontal | Visitor register: who is in the building, and who they came to see | 31 |
| `hm_license` | Horizontal | Offline licence verification for commercial Odoo modules | 73 |
| `hm_payroll` | Horizontal | Salary structures, rules and payslips for Odoo Community | 48 |
| `hm_purchase_request` | Horizontal | The step before the quotation: a department asks, and the request is approved on its own merits | 28 |
| `hm_roster` | Horizontal | Schedule guards, drivers or a reception desk, and be told when the roster is broken | 29 |

`af_*` modules are Afghanistan and Persian-market localization.
`hm_*` modules fill Odoo Community gaps and sell worldwide.

---

## Translations

1,911 translatable terms across the catalogue, of which 1,246 are distinct —
the rest are the chatter and activity labels every model inherits.

| Language | State |
|----------|-------|
| English | source |
| Dari (`fa_AF`) | all 1,911 terms — **a first draft, not reviewed by a native speaker** |
| Pashto (`ps_AF`) | not started — needs a translator |

CI installs the catalogue, activates `fa_AF` and reads Dari back out of the
database: 1,896 of 1,911 terms. The other 15 are translated to themselves —
date patterns and technical names — and Odoo stores no translation for a
string that equals its source.

### How it fits together

```bash
python tools/analyse_pot.py                      # what is in the templates
python tools/analyse_pot.py --untranslated fa_AF # coverage per module
python tools/analyse_pot.py --missing fa_AF hm_payroll
python tools/build_po.py fa_AF                   # write addons/*/i18n/fa_AF.po
```

Translations live in one memory per language, `tools/translations/<lang>.py`,
and `build_po.py` projects it onto every module. That is what stops twenty
modules inventing twenty words for "Cancel". The memory's docstring carries
the glossary and the reasoning behind each Afghan-versus-Iranian choice —
ولایت not استان, معاش not حقوق, مسوده not پیش‌نویس — which is the first thing a
reviewer should read.

### For a reviewer

Edit `addons/<module>/i18n/fa_AF.po` directly. `build_po.py` **keeps your
wording** where it differs from the memory and says so; `--harvest` then folds
your decision back in, and every other module picks it up.

Two things CI enforces, because both fail silently otherwise: the templates
must match the source (a string added and never re-exported cannot be
translated, because no translator ever sees it), and Dari must load — the
Odoo job activates `fa_AF`, exports it back out of the database, and counts
what came back.

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

## Packaging a release

```bash
python tools/build_release.py --all --plan        # what needs what
python tools/build_release.py af_jalali           # one module
python tools/build_release.py af_procurement --with-deps
python tools/build_release.py --suite hr          # a bundle
python tools/build_release.py --all               # every module, separately
```

`--plan` writes nothing and needs no signing key, so it works on any checkout.
Use it before quoting: it answers *what does this customer have to be licensed
for*, which is the dependency closure and not the one module they asked about.

### Dependencies are the thing that goes wrong

`af_procurement` needs `hm_purchase_request`, which needs `hm_approvals`, and
every paid module needs `hm_license`. Ship the one module a customer asked for
and Odoo refuses to install it — at their site, on the day they try. So the
closure is always computed: `--with-deps` bundles it, and without that flag the
tool prints exactly what else that customer must already have.

### Suites

| Suite | Sold as | Resolves to |
|---|---|---|
| `hr` | payroll, Afghan payroll, HR, rosters | 7 modules |
| `finance` | reports, assets, contracts, chart, dual currency, zakat | 8 |
| `office` | approvals, requests, comparison, letters, expiry, liaison, front desk | 9 |
| `afghanistan` | the whole `af_*` line | 15 |
| `complete` | everything | 20 |

**Note what `afghanistan` resolves to.** Selling the Afghan line alone hands
the customer `hm_approvals`, `hm_payroll`, `hm_purchase_request` and
`hm_expiry_docs` as dependencies — four of the horizontal modules, which are
the ones with the larger market. Price the suite accordingly, or the
localization line quietly gives away Line B.

Every run rewrites `dist/SHA256SUMS`, so a customer receiving a link can check
they got what was sent. `dist/` is git-ignored: archives are uploaded, never
committed, and a stale one in a working copy is a delivery waiting to go wrong.

---

## Before releasing any module

- [x] Installs on a clean database with no other addon present — the CI
      Odoo job builds one from scratch every push
- [x] `--test-enable` passes — CI greps the log for ERROR/CRITICAL, because
      Odoo exits 0 even when tests fail
- [x] `static/description/icon.png` (140×140) — generated by
      `python tools/generate_icons.py`, and CI fails if one is missing or a
      `web_icon` points at a file that is not there
- [x] `banner.png` drawn and the `images` key enabled — generated by
      `python tools/generate_icons.py`, and CI fails if one is missing or
      a declared image is not there
- [x] Demo data loads and shows something meaningful — CI loads it, because
      `--without-demo` is deliberately not passed
- [x] Templates exported and current — CI regenerates them every push and
      fails if they no longer match the source
- [x] Dari (`fa_AF`) complete — **first draft, not yet reviewed by a native
      speaker**
- [ ] Dari reviewed by a professional translator
- [ ] Pashto (`ps_AF`) — needs a translator; see below
- [x] RTL checked in Dari — the screens job activates `fa_AF`, drives all
      twenty screens again, and asserts the rendered direction really is
      right-to-left *and* the menus really are translated, because a
      language that fails to activate photographs perfectly in English
- [x] `static/description/index.html` — generated from
      `tools/listings/<module>.py`; CI fails if a page is stale or a module
      has no copy at all
- [x] `README.md` in the module — CI fails if one is missing
- [x] Every screen photographed on a real Odoo, in both languages, as a
      CI artifact
- [x] Demo data rich enough for those photographs to sell — payroll shows a
      computed payroll, timesheets show a submitted week and one in progress,
      and that submission is what puts a real request in the approvals queue
- [ ] Screenshots embedded in the listing pages (blocked on the above)
- [x] `CHANGELOG.md` written, with the versioning scheme recorded
- [ ] Version bumped for the release being cut
- [x] Delivery carries the modules it depends on — packaging resolves the
      closure, and refuses to leave a customer with an archive Odoo cannot
      install
- [x] Licence header on every file — all 157 Python files carry one
- [x] Gated behind `hm.license.gate`, or listed in `UNGATED` with a reason —
      CI fails if a module checks no licence, and packaging refuses it
- [ ] `VENDOR_PUBLIC_KEY` set to a real key — until then the gate is inert,
      and `tools/build_release.py` will not package anything
- [x] No AGPL dependency anywhere in the tree — CI fails on the string
