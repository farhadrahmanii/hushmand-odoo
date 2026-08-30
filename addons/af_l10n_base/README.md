# Afghanistan Localization Base

Afghan geography and identity fields for Odoo, as real data rather than
free-text boxes.

---

## What you get

| | |
|---|---|
| **34 provinces** | Loaded as Odoo country states, with published ISO 3166-2:AF codes |
| **546 districts** | Each linked to its province, selectable on any contact |
| **Villages** | Model and views, shipping empty (see below) |
| **Dari and Pashto** | Added as Odoo languages — Odoo ships neither |
| **Tazkira and TIN** | On every contact |
| **Afghan address layout** | Printed documents include the district |

Every place name is stored in **English, Dari and Pashto**, and shown in
whichever language the user reads.

---

## Why provinces are country states

Provinces are `res.country.state` records, not a separate model. That single
decision is what makes the module useful rather than isolated: provinces work
in **every address Odoo already has** — contacts, employees, invoices,
delivery addresses, portal forms — with nothing to configure and no other
module needing to know this one exists.

A standalone `af.province` model would have been an island that every other
feature had to be taught about.

Districts and villages are new models, because Odoo has no concept below the
state level.

---

## Dari and Pashto

Odoo ships **Persian (fa_IR) and nothing else** from the region. There is no
Dari and no Pashto, which means that without this module a customer cannot
select their own language at all.

This module creates both:

| Language | Code | Direction | Week starts |
|---|---|---|---|
| Dari / دری | `fa_AF` | Right to left | Saturday |
| Pashto / پښتو | `ps_AF` | Right to left | Saturday |

They are created inactive. Activate them in **Settings → Translations →
Languages**, or from the language selector in user preferences.

Pair this with `af_jalali` and dates become Jalali as well as the interface
becoming Dari.

---

## Villages ship empty, on purpose

The model, views and menu are all there, but no village data is loaded.

No trustworthy public dataset of Afghan villages exists, and the source ERP's
village table was never populated. Shipping invented data would be worse than
shipping none — a wrong village on an address is harder to spot than a missing
one. Add the villages your organisation actually works in.

---

## Using it

### On a contact

Province, district and village appear in the address block. Choosing a
district fills in the province automatically; changing the province clears a
district that no longer belongs to it.

### On a printed document

Afghanistan's address layout is set up during installation and includes the
village and district:

```
Street
Village
District
City  Postcode
Province
Afghanistan
```

### From Python

```python
kabul = self.env.ref('af_l10n_base.state_af_kab')
districts = self.env['af.district'].search([('state_id', '=', kabul.id)])

partner.af_district_id          # district record
partner.af_district_name        # plain text, usable in address formats
partner.af_tazkira              # national identity number
partner.af_tin                  # taxpayer identification number
```

---

## Data provenance

Provinces and districts come from a production ERP that has been in daily use
in Afghanistan for years, not from a scraped list. Before loading, the
extraction was checked: no blank names, no districts without a province, no
orphan references, no duplicates. Placeholder `UNKNOWN` rows were excluded.

One known gap: **Delaram** in Nimruz has no Pashto name in the source data, so
it falls back to the Dari spelling. The generator prints any district it had
to do that for, so the gap stays visible.

A note worth acting on: in the source data the Pashto province names are
copies of the Dari ones. They are correct for most provinces but not all. If
you have a Pashto speaker, reviewing the 34 province names is an hour of work
that would make the module noticeably better.

---

## Regenerating the data

The data files are generated, not hand-written:

```bash
python tools/generate_geography_data.py
```

Source: `tools/data/af_geography.json`. XML ids are derived from the ISO code
and the source row id, so re-running updates records in place instead of
creating duplicates.

---

## Compatibility

- Odoo **19.0** Community and Enterprise
- Depends on `base`, `contacts` and `hm_license`
- Installation instructions: see `af_jalali/INSTALL.md`, which applies here too
