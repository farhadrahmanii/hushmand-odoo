# Part of af_hr_payroll. See LICENSE file for full copyright and licensing details.
{
    "name": "Afghanistan Payroll",
    "summary": "Afghan wage withholding tax on a dated, editable scale, with "
               "salaries paid in dollars taxed in afghani",
    "description": """
Afghanistan Payroll
===================

Neither edition of Odoo has an Afghanistan payroll. Community has no payroll
engine at all, and Enterprise ships localizations for other countries. An
Afghan employer withholding tax from salaries has, until now, had a
spreadsheet.

This adds the Afghan part on top of the generic payroll engine: the wage
withholding scale, and a salary structure that uses it.

The scale is data, and it is dated
----------------------------------

Tax law changes. A rate compiled into a Python file means every customer waits
for a release, and every historical payslip silently recomputes on the new rate
the moment somebody reopens it. Here the brackets are an ordinary editable
table with a start date, so a payslip for last year stays taxed the way last
year was taxed.

The scale is validated as a scale. A gap between brackets leaves some salaries
untaxed and an overlap taxes some twice, and neither is visible until a payslip
is checked by hand, so the module refuses to save either. Each bracket carries
the tax already due at its floor, which keeps the scale continuous -- a salary
one afghani over a boundary pays one afghani's worth more tax, not a whole
band more.

Dollar salaries, afghani tax
----------------------------

Plenty of organisations in Kabul keep their books in dollars and pay staff in
dollars, but income tax is assessed in afghani. The tax rule converts the gross
to afghani at the month's agreed rate, applies the scale, and converts the
result back. If no confirmed exchange period covers the month it refuses to
compute rather than guessing, because a payslip is a legal document.

Periods that are not months
---------------------------

The scale is stated monthly. A fortnightly payslip is annualised before the
brackets are read, so half a month's pay is not mistaken for a poor salary and
taxed in a band the same annual wage would never reach.

A note on the supplied rates
----------------------------

The module ships the published monthly brackets so a new database computes
something sensible on day one. Confirm them against the Income Tax Law in
force before running real payroll. They are a starting point, not tax advice.
""",
    "version": "19.0.1.0.0",
    "category": "Human Resources/Payroll",
    "author": "Farhad Rahmani",
    "website": "https://hushmand.af",
    "license": "OPL-1",
    "depends": ["hm_payroll", "af_hr", "af_dual_currency", "hm_license"],
    "data": [
        "security/ir.model.access.csv",
        "data/af_income_tax_data.xml",
        "data/af_payroll_structure_data.xml",
        "views/af_income_tax_views.xml",
    ],
    "demo": [
        "demo/af_hr_payroll_demo.xml",
    ],
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
