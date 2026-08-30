# Part of af_dual_currency. See LICENSE file for full copyright and licensing details.
{
    "name": "Dual Currency by Exchange Period",
    "summary": "One agreed AFN/USD rate per month, locked once reported, "
               "with totals shown in both currencies",
    "description": """
Dual Currency by Exchange Period
================================

Odoo keeps one exchange rate per day and converts using the nearest one. That
suits a business marking to market daily. It does not suit an organisation
that fixes a single rate for a whole month and uses it for payroll, tax
filings and every document issued in that month.

Two things are missing from the plain rate table, and this module adds them.

**One agreed rate per period.** Define a period, set the rate, confirm it.
Every document dated inside the period uses that rate.

**Rates that stop changing.** Closing a period locks the rate. Nobody can
quietly edit a figure that has already been reported to the ministry, and
reopening one is a deliberate act that warns you what it means.

Confirming a period writes an ordinary Odoo currency rate, so invoices,
accounting and every existing report keep working exactly as before. The
module adds governance on top of Odoo's mechanism rather than replacing it.

Also included
-------------

* The afghani, activated. It ships with Odoo but switched off.
* A second-currency total on invoices and bills, with the period that produced
  it, so any figure can be traced back to an agreed rate.
* A helper other modules can call, used by the Afghan payroll module to put
  gross, tax and net on a payslip in both currencies.

Useful anywhere a second currency has to be reported at an agreed rate rather
than a floating one.
""",
    "version": "19.0.1.0.0",
    "category": "Accounting/Localizations",
    "author": "Farhad Rahmani",
    "website": "https://hushmand.af",
    "license": "OPL-1",
    "depends": ["base", "base_setup", "account", "hm_license"],
    "data": [
        "security/ir.model.access.csv",
        "data/res_currency_data.xml",
        "views/af_exchange_period_views.xml",
        "views/res_config_settings_views.xml",
        "views/account_move_views.xml",
        "views/menus.xml",
    ],
    "demo": [
        "demo/af_dual_currency_demo.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
