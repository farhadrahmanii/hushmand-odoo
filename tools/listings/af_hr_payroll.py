LISTING = {
    "eyebrow": "Human Resources · Localization",
    "title": "Afghanistan Payroll",
    "lede": "Afghan wage withholding tax, on a dated and editable scale — with "
            "salaries paid in dollars assessed in afghani, the way the law reads.",
    "callout": (
        "Neither edition of Odoo has an Afghanistan payroll.",
        "Community has no payroll engine at all, and Enterprise ships localizations for "
        "other countries. An Afghan employer withholding tax from salaries has, until "
        "now, had a spreadsheet.",
    ),
    "blocks": [
        {
            "h2": "The scale is data, and it is dated",
            "text": [
                "Tax law changes. A rate compiled into a Python file means every "
                "customer waits for a release — and every historical payslip silently "
                "recomputes on the new rate the moment somebody reopens it.",
                "Here the brackets are an ordinary editable table with a start date, so "
                "a payslip for last year stays taxed the way last year was taxed. When "
                "rates change you close the scale with an end date and create the next "
                "one.",
            ],
        },
        {
            "h2": "The scale is validated as a scale",
            "bullets": [
                ("No gaps, no overlaps", "a gap leaves some salaries untaxed and an "
                 "overlap taxes some twice — neither is visible until a payslip is "
                 "checked by hand, so the module refuses to save either"),
                ("The lowest bracket starts at zero", "or salaries below it are not "
                 "taxed at all"),
                ("The highest is open-ended", "or a large enough salary falls off the "
                 "top of the scale untaxed"),
                ("Each bracket carries the tax due at its floor", "which is what keeps "
                 "the rate applying only to the part of the salary inside the bracket"),
            ],
        },
        {
            "h2": "Paid in dollars, taxed in afghani",
            "text": [
                "Afghan tax is assessed in afghani. A salary paid in dollars is "
                "therefore converted before the scale is applied — at the rate agreed "
                "for that month, from <code>af_dual_currency</code>, not at whatever "
                "the daily table happened to hold.",
                "If no confirmed exchange period covers the payslip, the module refuses "
                "to compute rather than picking a rate. It tells you which month to "
                "confirm.",
            ],
        },
        {
            "h2": "What it adds to a payslip",
            "bullets": [
                ("A ready salary structure", "using the scale, with income tax withheld "
                 "as its own line"),
                ("Advance recovery", "the instalment due, deducted and shown"),
                ("Statutory brackets preloaded", "as a starting point you can edit — "
                 "check them against current Afghanistan Revenue Department guidance "
                 "before filing"),
            ],
        },
    ],
    "footer": "Odoo 19.0 Community · depends on <code>hm_payroll</code>, "
              "<code>af_hr</code> and <code>af_dual_currency</code>.",
}
