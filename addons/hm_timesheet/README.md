# Timesheets

Weekly timesheets that get submitted, approved, locked and printed.

---

## Why this exists

Odoo Community records time on tasks perfectly well. `hr_timesheet` gives
every employee an entry per piece of work, and the list and pivot views to read
them back.

What it has no concept of is a **week that gets submitted**. There is nothing
to approve, nothing that locks once approved, and nothing to print and sign.
That is Enterprise's `timesheet_grid`.

This module adds that layer and deliberately adds only that.

---

## A window, not a second store

Entries stay ordinary `account.analytic.line` records. A sheet is a window onto
the entries that fall inside its week:

```
account.analytic.line.sheet_id  ->  hm.timesheet.sheet
        (employee + date)              (employee + week)
```

Consequences worth knowing:

- Every existing timesheet report, filter and export keeps working. Nothing is
  entered twice.
- Logging time **creates the week** if it is not there. Nobody has to open a
  timesheet before recording work.
- A new sheet **adopts** entries already in its week. Time logged before anyone
  opened a timesheet still belongs to the week it was worked in.
- Moving an entry to another date **moves it to the right week**. Left attached
  to the old sheet it would keep counting towards a week it is not in, and both
  weeks' totals would be wrong.

An analytic line that is not a timesheet — a cost allocation, a revenue split —
is left alone. A line only belongs on a timesheet when it says who worked, on
what, and when.

---

## The lock

| State | Entries can be | Who moves it on |
|---|---|---|
| Draft | added, changed, deleted | the employee submits |
| Submitted | nothing | an approver approves or sends it back |
| Approved | nothing | only cancelling the approval reopens it |
| Rejected | added, changed, deleted | the employee fixes it and resubmits |

Adding a *new* entry to a submitted week is refused as well. A lock that only
guards the entries already there is not a lock.

The one write a locked sheet still accepts is `sheet_id` itself, because
otherwise the module could never attach anything.

> An approved statement of hours that can still be edited underneath the
> approver is not an approval. It is usually discovered by payroll, a month
> later, on a figure somebody has already been paid against.

---

## Approval is configuration, not code

Routing comes from **Approval Workflows** (`hm_approvals`), so who signs off, in
what order, and under what conditions is set up by the customer:

| Week | Route |
|---|---|
| Under 45 hours | Line manager |
| Over 45 hours | Line manager, then the department head |

Approvers can be resolved from the sheet itself — `employee_id.parent_id.user_id`
— so the employee's own manager is found rather than named, and the process
survives people changing roles.

---

## The week

Saturday to Friday by default, because that is the Afghan working week.
Configurable per company in **Settings → General Settings → Timesheets**.

Values are Odoo's own ISO weekday numbers, 1 for Monday through 7 for Sunday,
the same convention `res.lang.week_start` uses.

Any date written to `date_start` is snapped back to the first day of its week,
so a sheet cannot straddle two.

---

## Expected hours

Read from the employee's own working calendar, summed from their real
attendances rather than from `hours_per_day`:

```
expected = sum(attendance.hour_to - attendance.hour_from)
```

`hours_per_day` is an average, and four nine-hour days is not five seven-hour
ones. A two-week calendar holds two weeks of attendances, so its total is
halved.

`difference_hours` is recorded minus expected, **stored**, and searchable —
there is a *Short of Expected* filter. It is stored because a search-view
filter on a non-stored computed field does not merely fail: it refuses the
whole registry load and every module in the database stops installing.

---

## Printing

A weekly grid: projects and tasks down, the seven days across, totals both
ways, and signature lines for the employee and the approver.

`_report_grid()` builds it. A flat list of entries answers neither "what did
this project take this week" nor "what did Tuesday look like" without the
reader adding up.

---

## Security

No new groups. `hr_timesheet` already divides the world into people who see
their own timesheets, people who see everyone's, and administrators.

| Group | Sees |
|---|---|
| `group_hr_timesheet_user` | their own weeks |
| `group_hr_timesheet_approver` | every week |
| `group_timesheet_manager` | every week, and may delete |

---

## Compatibility

- Odoo **19.0** Community and Enterprise
- Depends on `hr_timesheet`, `hm_approvals` and `hm_license`
- Installation instructions: see `af_jalali/INSTALL.md`
