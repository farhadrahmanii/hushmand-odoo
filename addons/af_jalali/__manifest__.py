# Part of af_jalali. See LICENSE file for full copyright and licensing details.
{
    "name": "Jalali Calendar (Afghan & Persian)",
    "summary": "Hijri-Shamsi dates across Odoo, with Afghan and Iranian month names",
    "description": """
Jalali (Hijri-Shamsi) Calendar for Odoo
=======================================

Adds the Solar Hijri calendar to Odoo without changing how dates are stored.
Everything stays Gregorian in the database, so reporting, imports and every
other module keep working exactly as before.

* Accurate conversion for Jalali years -61 to 3177
* **Afghan month names** (Hamal, Sawr, Jawza) as well as Iranian ones
  (Farvardin, Ordibehesht, Khordad) -- switchable per company
* English, Dari and Pashto, including month and weekday names
* Saturday-first week, matching the Afghan working week
* Persian numerals, optional
* Per-user override: staff working with foreign partners can stay on Gregorian
* Prints Jalali on any report with a single ``t-options`` attribute
* Timezone aware, so an evening entry in Kabul does not slip to the day before

Built for organisations operating in Afghanistan, and usable anywhere the
Solar Hijri calendar is.
""",
    "version": "19.0.1.0.0",
    "category": "Localization",
    "author": "Farhad Rahmani",
    "website": "https://hushmand.af",
    "license": "OPL-1",
    "depends": ["base", "base_setup", "web"],
    "data": [
        "views/res_config_settings_views.xml",
        "views/res_users_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "af_jalali/static/src/js/jalali.js",
            "af_jalali/static/src/js/jalali_date_field.js",
            "af_jalali/static/src/xml/jalali_date_field.xml",
            "af_jalali/static/src/scss/jalali.scss",
        ],
    },
    # "images": ["static/description/banner.png"],  # add before release
    "installable": True,
    "application": False,
    "auto_install": False,
}
