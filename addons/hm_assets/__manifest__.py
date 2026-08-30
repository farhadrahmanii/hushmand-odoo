# Part of hm_assets. See LICENSE file for full copyright and licensing details.
{
    "name": "Fixed Assets",
    "summary": "Asset register and depreciation for Odoo Community",
    "description": """
Fixed Assets
============

Odoo's asset management is Enterprise. A Community user who buys a vehicle
has a bill and nothing else: no register, no depreciation, and a balance sheet
that overstates what the company owns for the rest of the asset's life.

This adds the register and the schedule.

* **Straight line** or **reducing balance**, monthly, quarterly or yearly.
* **Prorated first period**, so an asset bought on the last day of the year is
  not charged a full year of depreciation.
* **Salvage value** is never depreciated past.
* **Categories** carry the defaults, so recording a vehicle does not mean
  choosing four accounts every time.

Nothing posts by itself
-----------------------

The schedule is a forecast until somebody confirms a period. There is no cron
quietly writing entries into a month that has been closed. Recomputing the
schedule leaves posted periods untouched and reschedules only what is left,
and a posted period cannot afterwards be edited or deleted -- to change it you
reverse its journal entry, so the ledger keeps a record of both.
""",
    "version": "19.0.1.0.0",
    "category": "Accounting/Accounting",
    "author": "Farhad Rahmani",
    "website": "https://hushmand.af",
    "license": "OPL-1",
    "depends": ["account", "hm_license"],
    "data": [
        "security/ir.model.access.csv",
        "views/hm_asset_views.xml",
    ],
    "demo": [
        "demo/hm_assets_demo.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
