# Part of hm_account_reports. See LICENSE file for full copyright and licensing details.
{
    "name": "Financial Reports",
    "summary": "Trial balance, profit and loss, and balance sheet for "
               "Odoo Community",
    "description": """
Financial Reports
=================

Odoo Community gives you journal items and a chart of accounts, and then
stops. There is no trial balance, no profit and loss, no balance sheet.
Odoo's dynamic reports are Enterprise, so a Community user who has to file
accounts or hand something to an auditor has nothing to hand them.

This adds the three statements every accountant asks for first.

**Trial Balance** with opening, movement and closing figures per account.
Income and expense accounts show no opening balance, because they reset each
financial year and a brought-forward figure there would be wrong.

**Profit and Loss** grouped into operating income, other income, cost of
revenue, operating expenses, depreciation and other expenses.

**Balance Sheet** as at a date, including the current period's result as
equity. That result is not sitting in an account until the year is closed, so
without it the sheet does not balance -- and the report says so plainly if the
two sides ever disagree.

Filters
-------

Restrict any statement by date, journal, company or analytic account. Draft
entries are excluded by default, and if you include them the report says on
its face that it is not suitable for filing.
""",
    "version": "19.0.1.0.0",
    "category": "Accounting/Accounting",
    "author": "Farhad Rahmani",
    "website": "https://hushmand.af",
    "license": "OPL-1",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "report/hm_account_report_templates.xml",
        "views/hm_account_report_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
