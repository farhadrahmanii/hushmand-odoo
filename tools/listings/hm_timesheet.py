LISTING = {
    "eyebrow": "Human Resources",
    "title": "Timesheets for Odoo Community",
    "lede": "Weekly timesheets that get submitted, approved, locked and "
            "printed — the layer Community is missing, built on the timesheet "
            "entries it already has.",
    "callout": (
        "Community records the hours. It has no concept of a week.",
        "<code>hr_timesheet</code> gives every employee an entry per piece of "
        "work. There is nothing to approve, nothing that locks once approved, "
        "and nothing to print and sign. That is Enterprise's Timesheets Grid.",
    ),
    "blocks": [
        {
            "h2": "A window, not a second place to type",
            "text": [
                "Entries stay ordinary analytic lines. A timesheet is a window "
                "onto the entries that fall inside its week, so every report, "
                "filter and export that already reads Odoo timesheets keeps "
                "working and nothing is entered twice.",
                "Time logged before anyone opened a timesheet is adopted by the "
                "week it was worked in. Move an entry to another date and it "
                "moves to the right week with it, instead of quietly counting "
                "towards the wrong one.",
            ],
        },
        {
            "h2": "Approved means approved",
            "table": {
                "head": ["State", "Entries can be", "Who moves it on"],
                "rows": [
                    ["Draft", "added, changed, deleted", "the employee submits"],
                    ["Submitted", "nothing — locked",
                     "an approver approves or sends it back"],
                    ["Approved", "nothing — locked",
                     "only cancelling the approval reopens it"],
                    ["Rejected", "added, changed, deleted",
                     "the employee fixes it and resubmits"],
                ],
            },
        },
        {
            "h2": "Why the lock is the point",
            "text": [
                "An approved statement of hours that can still be edited "
                "underneath the approver is not an approval. It is the failure "
                "that makes people stop trusting the numbers — and it is "
                "usually discovered by payroll, a month later, on a figure "
                "somebody has already been paid against.",
                "Adding a new entry to a submitted week is refused too, which "
                "is the obvious way round a lock that only guards the entries "
                "already there.",
            ],
        },
        {
            "h2": "Who approves it is configuration",
            "text": [
                "Routing comes from <strong>Approval Workflows</strong>, so a "
                "timesheet can go to the line manager, or the project manager, "
                "or both above a certain number of hours — without a developer. "
                "Approvers can be resolved from the sheet itself, so the "
                "employee's own manager is found rather than named, and the "
                "process survives people changing roles.",
            ],
        },
        {
            "h2": "Also included",
            "bullets": [
                ("A week that starts on Saturday", "the Afghan working week, "
                 "and a setting for everywhere else"),
                ("Expected hours from the employee's own calendar", "summed "
                 "from their real attendances, so four nine-hour days is not "
                 "confused with five seven-hour ones"),
                ("The difference, searchable", "a filter for weeks that came "
                 "in short, before payroll asks"),
                ("A printed weekly grid", "projects down, days across, totals "
                 "both ways, and two signature lines"),
            ],
        },
    ],
    "footer": "Odoo 19.0 Community · depends on <code>hr_timesheet</code> and "
              "<code>hm_approvals</code>. Entries remain "
              "<code>account.analytic.line</code> records.",
}
