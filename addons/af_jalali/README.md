# Jalali Calendar (Afghan & Persian)

Solar Hijri dates throughout Odoo, without changing how anything is stored.

Dates remain Gregorian in the database. Reporting, imports, exports, the API
and every other module keep working exactly as before — only what people read
changes.

---

## Why not a generic Jalali module

Afghanistan and Iran share the calendar but not the month names:

| # | Afghan | Iranian |
|---|--------|---------|
| 1 | Hamal / حمل | Farvardin / فروردین |
| 2 | Sawr / ثور | Ordibehesht / اردیبهشت |
| 3 | Jawza / جوزا | Khordad / خرداد |
| 6 | **Sunbula / سنبله** | **Shahrivar / شهریور** |

A module shipping only the Iranian names is wrong on every Afghan document.
This one carries both, plus **Pashto** month names (وری, غويی, غبرګولی …),
which almost nothing else does, and a Saturday-first week to match the Afghan
working week.

---

## Using it

### In a form or list view

```xml
<field name="date_start" widget="jalali_date"/>
<field name="create_date" widget="jalali_datetime"/>
<field name="date_start" widget="jalali_date" options="{'format': 'dd MMMM yyyy'}"/>
```

The field accepts typed input in Jalali — `1405/06/02`, `۱۴۰۵/۰۶/۰۲`,
`2 Sunbula 1405` all work — and stores the Gregorian equivalent. Hovering shows
the Gregorian date, so anyone can cross-check.

### On a printed report

```xml
<span t-field="doc.date_order" t-options='{"widget": "jalali"}'/>
<span t-field="doc.date_order"
      t-options='{"widget": "jalali", "format": "EEEE، dd MMMM yyyy"}'/>
```

### From Python

```python
service = self.env['af.jalali']
service.format_date(record.date_start)                  # 1405/06/02
service.format_date(record.date_start, 'dd MMMM yyyy')  # 02 Sunbula 1405
service.format_datetime(record.create_date)             # timezone aware
service.parse('1405/06/02')                             # datetime.date(2026, 8, 24)
service.try_parse(user_input)                           # None instead of raising
```

---

## Format patterns

| Token | Output | Token | Output |
|-------|--------|-------|--------|
| `yyyy` | 1405 | `dd` | 02 |
| `yy` | 05 | `d` | 2 |
| `MMMM` | Sunbula | `EEEE` | Doshanbe |
| `MMM` | Sun | `HH` `mm` `ss` | 14 05 09 |
| `MM` | 06 | | |
| `M` | 6 | | |

**Literal words must be quoted**, the ICU convention:

```
'Issued on' dd/MM/yyyy    ->  Issued on 02/06/1405
```

Without quotes the `ss` and `d` inside "Issued" are read as tokens. Use `''`
for a literal apostrophe. Separators (`/ - . space`) need no quoting.

---

## Settings

**Settings → General Settings → Calendar**

| Setting | Effect |
|---------|--------|
| Jalali Calendar | Turn the calendar on for the company |
| Month Names | Afghan or Iranian |
| Date Format | Default pattern, e.g. `yyyy/MM/dd` |
| Date and Time Format | Default pattern with time |
| Persian Digits | Render ۱۴۰۵ instead of 1405 |

Each user can override the company default in **Preferences → Calendar**, so
staff working with foreign partners can stay on Gregorian.

---

## Correctness

The conversion is verified against the reference `jalaali` implementation over
**every day from 1900-01-01 to 2100-12-31** — 73,414 dates — plus 201
leap-year and month-length checks. The Python and JavaScript implementations
are diffed against each other on every run of:

```bash
python tools/verify_js_python_parity.py
```

This matters: reports render in Python and forms render in JavaScript. If they
disagreed, a printed payslip would show a different date from the screen it was
generated from.

Tests that need no Odoo installation:

```bash
python tools/run_core_tests.py
```

---

## Architecture

| Tier | Location | Portability |
|------|----------|-------------|
| 0 | `core/` | Pure Python, no Odoo imports. Valid on every Odoo version |
| 1 | `models/` | Long-stable ORM APIs only |
| 2 | `views/`, `static/` | Version-specific; the only place a port should touch |

Two spots are worth re-checking on a new Odoo release, and both are commented
in the source: `SELF_READABLE_FIELDS` in `models/res_users.py`, and the imports
at the top of `static/src/js/jalali_date_field.js`.

---

## Compatibility

- Odoo **19.0** Community and Enterprise
- Depends on `base`, `base_setup`, `web` and `hm_license` — no third-party
  libraries
- Jalali years −61 to 3177
