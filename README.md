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

| Module | Line | Status |
|--------|------|--------|
| `af_jalali` | Afghanistan | **Built** — Jalali calendar, Afghan and Iranian month names |
| `af_l10n_base` | Afghanistan | Next |
| `af_dual_currency` | Afghanistan | Planned |
| `hm_approvals` | Horizontal | Planned |

`af_*` modules are Afghanistan and Persian-market localization.
`hm_*` modules fill Odoo Community gaps and sell worldwide.

---

## Before releasing any module

- [ ] Installs on a clean database with no other addon present
- [ ] `--test-enable` passes
- [ ] `static/description/icon.png` (140×140) and `banner.png` drawn, and the
      `images` key re-enabled in the manifest
- [ ] Demo data loads and shows something meaningful
- [ ] Translations exported and `fa` / `ps` filled in
- [ ] RTL checked visually in Dari
- [ ] `static/description/index.html` written, with screenshots
- [ ] Version bumped, changelog updated
- [ ] Licence header on every file
- [ ] No AGPL dependency anywhere in the tree
