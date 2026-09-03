# Part of hm_timesheet. See LICENSE file for full copyright and licensing details.
{
    "name": "Timesheets",
    "summary": "Weekly timesheets that get submitted, approved, locked and printed",
    "description": """
Timesheets
==========

Odoo Community records time on tasks perfectly well. ``hr_timesheet`` gives
every employee an entry per piece of work, and the list and pivot views to
read them back.

What it has no concept of is a **week that gets submitted**. There is nothing
to approve, nothing that locks once approved, and nothing to print and sign.
That is Enterprise's Timesheets Grid, and this is that layer, built on
Community.

A window, not a second store
----------------------------

Entries stay ordinary analytic lines. A timesheet is a window onto the entries
that fall inside its week, so every report, filter and export that already
reads Odoo timesheets keeps working, and nothing has to be entered twice.

Time logged before anyone opened a timesheet is adopted by the week it was
worked in. Move an entry to another date and it moves to the right week with
it, instead of quietly counting towards the wrong one.

Approved means approved
-----------------------

Once a week is submitted its entries cannot be added to, changed or deleted.
An approved statement of hours that can still be edited underneath the
approver is not an approval, and it is the failure that makes people stop
trusting the numbers.

Reopening is a deliberate act, and an approved week cannot be reopened at all
without cancelling the approval first.

Who approves it is configuration
--------------------------------

Routing comes from **Approval Workflows**, so a timesheet can go to the line
manager, or to the project manager, or to both above a certain number of
hours, without a developer. Approvers can be resolved from the sheet itself,
so the employee's own manager is found rather than named.

Also included
-------------

* **The week starts on Saturday**, which is the Afghan working week, and is a
  setting for everywhere else.
* **Expected hours** read from the employee's own working calendar, and the
  difference against what they recorded, so a short week is visible before
  payroll asks.
* **A printed weekly grid** -- projects down, days across, totals both ways --
  to sign and file.
""",
    "version": "19.0.1.0.0",
    "category": "Human Resources",
    "author": "Farhad Rahmani",
    "website": "https://hushmand.af",
    "license": "OPL-1",
    "depends": ["hr_timesheet", "hm_approvals", "hm_license"],
    "data": [
        "security/hm_timesheet_security.xml",
        "security/ir.model.access.csv",
        "views/hm_timesheet_sheet_views.xml",
        "views/res_config_settings_views.xml",
        "report/hm_timesheet_report.xml",
    ],
    "demo": [
        "demo/hm_timesheet_demo.xml",
    ],
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": True,
    "auto_install": False,
}
