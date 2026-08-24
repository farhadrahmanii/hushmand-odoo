# Translations

The `.pot` template is generated from a running Odoo, not by hand:

```bash
docker compose exec odoo odoo -d dev --i18n-export=/mnt/extra-addons/af_jalali/i18n/af_jalali.pot --modules=af_jalali --stop-after-init
```

Then merge into the language files:

```bash
msgmerge --update fa.po af_jalali.pot
msgmerge --update ps.po af_jalali.pot
```

## Status

| Language | Code | State |
|----------|------|-------|
| English  | en   | Source |
| Dari     | fa   | Field labels done, help text pending |
| Pashto   | ps   | Field labels done, help text pending |

Month and weekday names are **not** translated through `.po` files -- they live
in `core/formats.py` and `static/src/js/jalali.js`, because they must be
identical on both sides and must not depend on the user's language pack being
installed.

## Before release

- [ ] Regenerate the `.pot`
- [ ] Fill every `msgstr` in `fa.po` and `ps.po`
- [ ] Check RTL rendering with `lang=fa` -- especially the settings page
- [ ] Confirm no English text leaks into a Dari-only screen
