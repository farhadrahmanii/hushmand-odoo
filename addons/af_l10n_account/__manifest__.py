# Part of af_l10n_account. See LICENSE file for full copyright and licensing details.
{
    "name": "Afghanistan - Accounting",
    "summary": "Chart of accounts and taxes for Afghanistan",
    "description": """
Afghanistan - Accounting
========================

Odoo ships 225 fiscal localizations. Afghanistan is not among them, in either
edition. An Afghan company installing Odoo today builds a chart of accounts
from nothing and gets the tax treatment wrong on the way.

This provides:

* a **chart of accounts** structured for Afghan businesses and NGOs, with dual
  AFN and USD cash and bank accounts, staff advances, and the fixed-asset and
  accumulated-depreciation pairs that pair with the Fixed Assets module;
* **Business Receipts Tax** at 2%, 4% and 10%;
* **withholding taxes** on contractors (2% licensed, 7% unlicensed) and rent
  (10% and 15%), posting to separate liability accounts because they are filed
  separately.

On the rates
------------

Afghan tax rates and thresholds change, and enforcement has varied. The rates
here reflect the long-standing Business Receipts Tax and withholding regime,
but **confirm them against current Afghanistan Revenue Department guidance
before filing anything**. They are ordinary Odoo taxes and can be edited.

There is no chart of accounts mandated for private companies in Afghanistan,
so the structure here is conventional rather than official. It is a starting
point that a local accountant can adjust, which is a great deal better than an
empty database.
""",
    "version": "19.0.1.0.0",
    "category": "Accounting/Localizations/Account Charts",
    "author": "Farhad Rahmani",
    "website": "https://hushmand.af",
    "license": "OPL-1",
    "countries": ["af"],
    "depends": ["account"],
    # Odoo's own localizations auto-install alongside account. This one does
    # not: it is a paid module in a catalogue where several other modules run
    # their own accounting tests, and a chart that installs itself would
    # change the chart under them. The customer installs it deliberately.
    "auto_install": False,
    "installable": True,
    "application": False,
}
