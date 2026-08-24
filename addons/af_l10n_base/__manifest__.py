# Part of af_l10n_base. See LICENSE file for full copyright and licensing details.
{
    "name": "Afghanistan Localization Base",
    "summary": "Afghan provinces and districts, tazkira and TIN fields, "
               "trilingual and ready to use",
    "description": """
Afghanistan Localization Base
=============================

The geography and identity fields every Afghan organisation needs, as real
data rather than free-text boxes.

* **34 provinces** loaded as Odoo country states, with the published
  ISO 3166-2:AF codes. Because they are country states, provinces work in
  every address Odoo already has -- partners, employees, invoices, delivery
  addresses -- with nothing else to configure.
* **546 districts**, linked to their province, selectable on any contact.
* **Villages**, structure provided for organisations that work at that level.
* Every place name in **English, Dari and Pashto**, shown in whichever
  language the user reads.
* **Tazkira** and **TIN** fields on contacts.
* Afghan address layout on printed documents, including the district.

The province and district data comes from a production ERP that has been in
daily use in Afghanistan for years, not from a scraped list.
""",
    "version": "19.0.1.0.0",
    "category": "Localization",
    "author": "Farhad Rahmani",
    "website": "https://hushmand.af",
    "license": "OPL-1",
    "depends": ["base", "contacts"],
    "data": [
        "security/ir.model.access.csv",
        "data/res_country_state_data.xml",
        "data/af_district_data.xml",
        "data/res_country_data.xml",
        "views/af_district_views.xml",
        "views/af_village_views.xml",
        "views/res_partner_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
