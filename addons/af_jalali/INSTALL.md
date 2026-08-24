# Installing the Jalali Calendar module

Odoo **19.0**, Community or Enterprise, self-hosted.

> **Odoo Online (odoo.com) cannot install this module.** The SaaS platform does
> not allow custom code. You need a self-hosted Odoo, or Odoo.sh. This is a
> platform restriction, not something the module can work around.

---

## Step 1 — Put the module where Odoo can see it

Odoo only loads modules from directories listed in its **addons path**. Pick the
method that matches how your Odoo runs.

### If you run Odoo in Docker

Mount the folder containing `af_jalali` into the container and add it to the
addons path:

```yaml
volumes:
  - ./addons:/mnt/extra-addons
command: >
  odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons
```

The folder you mount is the **parent**. If the module is at
`./addons/af_jalali/`, mount `./addons`, not `./addons/af_jalali`.

### If Odoo is installed directly on a server

Copy the `af_jalali` folder into your addons directory — commonly
`/opt/odoo/custom-addons/` or `/usr/lib/python3/dist-packages/odoo/addons/` —
then make sure that directory appears in `addons_path` in your `odoo.conf`:

```ini
[options]
addons_path = /usr/lib/python3/dist-packages/odoo/addons,/opt/odoo/custom-addons
```

Odoo must be able to read the files:

```bash
chown -R odoo:odoo /opt/odoo/custom-addons/af_jalali
chmod -R a+rX /opt/odoo/custom-addons/af_jalali
```

### If you use Odoo.sh

Commit the `af_jalali` folder to your Odoo.sh repository and push. The platform
rebuilds and picks it up automatically.

---

## Step 2 — Restart Odoo

Odoo reads the addons path only at startup. Nothing you do in the interface
will find the module until you restart.

```bash
docker compose restart odoo      # Docker
sudo systemctl restart odoo      # system service
```

---

## Step 3 — Install it

### Option A: from the interface

1. **Enable developer mode.**
   Settings → scroll to the bottom → Developer Tools → **Activate the developer
   mode**. Without this the next step's menu is hidden.

2. **Update the apps list.**
   Apps → the **Update Apps List** menu appears in the top bar → confirm.
   Odoo now rescans the addons path.

3. **Find the module — this is where most people get stuck.**
   Go to Apps and search for `Jalali`. If nothing comes up, **remove the
   "Apps" filter** in the search box first. That filter hides everything that
   is not a full application, and this module is a technical module, so it is
   filtered out by default. Clear the filter and it appears.

4. Click **Activate** (older versions say Install). Takes a few seconds.

### Option B: from the command line

Faster, and it does not need developer mode:

```bash
odoo -d YOUR_DATABASE -i af_jalali --stop-after-init
```

In Docker:

```bash
docker compose run --rm odoo odoo -d YOUR_DATABASE -i af_jalali --stop-after-init
```

Then start Odoo normally again.

---

## Step 4 — Turn the calendar on

Installing the module does not switch the calendar on by itself — that is
deliberate, so installing it never changes what your staff see without someone
deciding to.

**Settings → General Settings → Calendar**

| Setting | What to choose |
|---|---|
| Jalali Calendar | Tick it |
| Month Names | **Afghan** (Hamal, Sawr, Jawza) or Iranian (Farvardin…) |
| Date Format | `yyyy/MM/dd` is the default. Try `dd MMMM yyyy` for month names |
| Persian Digits | Optional — shows ۱۴۰۵ instead of 1405 |

Save.

Individual users can override this in **Preferences → Calendar** (click your
avatar, top right) — useful for staff who work with foreign partners and want
to stay on Gregorian.

---

## Step 5 — Check it works

The module adds the calendar engine; it does not silently rewrite every date
field in Odoo. To see it, put the widget on a field:

1. With developer mode on, open any form with a date.
2. Or add it in a view: `<field name="date_start" widget="jalali_date"/>`

Type `1405/06/02` into a Jalali field and save — it stores 24 August 2026.
Hover over the field and it shows you the Gregorian date, so you can always
cross-check.

On a printed report:

```xml
<span t-field="doc.date_order" t-options='{"widget": "jalali"}'/>
```

---

## Updating to a newer version

Replace the module folder with the new one, restart Odoo, then:

```bash
odoo -d YOUR_DATABASE -u af_jalali --stop-after-init
```

Or from the interface: Apps → find the module → **Upgrade**.

Your settings and data are preserved.

---

## Uninstalling

Apps → find the module → the ⋮ menu → **Uninstall**.

Nothing is lost. Dates were always stored as Gregorian, so removing the module
just returns the display to Gregorian.

---

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Module does not appear in Apps | The **Apps filter** is hiding it. Clear the filter, then search `Jalali` |
| Still not there after clearing the filter | Odoo cannot see the folder. Check `addons_path`, check file permissions, then restart Odoo and update the apps list again |
| "Update Apps List" menu is missing | Developer mode is off. Settings → bottom of the page → Activate developer mode |
| Dates still show as Gregorian | The calendar is off. Settings → General Settings → Calendar. Also check your own Preferences → Calendar is not set to "Always Gregorian" |
| Month names look Iranian, not Afghan | Settings → General Settings → Calendar → Month Names → Afghan |
| A date is one day off | Almost always a timezone issue. Set your timezone in Preferences (Asia/Kabul). Odoo stores times in UTC and the module converts to your timezone |
| Install fails, log shows a view error | You are not on Odoo 19.0. Check with `odoo --version`; this build targets 19.0 |

---

## Support

Farhad Rahmani — wardak2023@gmail.com
