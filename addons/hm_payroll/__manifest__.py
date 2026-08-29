# Part of hm_payroll. See LICENSE file for full copyright and licensing details.
{
    "name": "Payroll",
    "summary": "Salary structures, rules and payslips for Odoo Community",
    "description": """
Payroll
=======

Payroll is the single biggest gap in Odoo Community. The ``hr`` module knows
what an employee earns -- ``hr.version`` carries the wage -- and then nothing
turns that wage into a payslip, a deduction, or a journal entry.

This module is that engine.

* **Salary structures** hold an ordered list of rules and belong to a
  structure type from core ``hr``, so employees pick them up naturally.
* **Salary rules** compute a fixed amount, a percentage of any base, or the
  result of a Python expression with the employee, the contract version, the
  other inputs and the running category totals in scope.
* **Payslips** are computed on demand, line by line, in rule order -- so a
  Net rule can see what Gross came to, exactly the way a payroll officer
  works down a sheet.
* **Batches** generate one payslip per employee for a period and confirm
  them together.

Nothing posts by itself
-----------------------

Computing a payslip writes nothing to the ledger. Confirming it creates a
**draft** journal entry -- aggregated per account, refused outright if the
configured accounts do not balance -- and an accountant posts it. There is
no cron and no silent write into a closed month.

A payslip whose entry has been posted cannot be cancelled; reverse the entry
first, so the ledger keeps a record of both.

What this module is not
-----------------------

It has no country content: no tax brackets, no social security, no statutory
reports. Those belong in localization modules built on top of this one. The
engine stays generic so that it works anywhere.
""",
    "version": "19.0.1.0.0",
    "category": "Human Resources/Payroll",
    "author": "Farhad Rahmani",
    "website": "https://hushmand.af",
    "license": "OPL-1",
    "depends": ["hr", "account", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/hm_salary_rule_category_data.xml",
        "views/hm_payroll_views.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
