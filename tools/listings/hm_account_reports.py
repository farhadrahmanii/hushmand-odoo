LISTING = {
    "eyebrow": "Accounting",
    "title": "Financial Reports for Odoo Community",
    "lede": "Trial balance, profit and loss, and balance sheet — the three statements "
            "every accountant asks for first, and the three Community does not have.",
    "callout": (
        "Community gives you journal items and a chart of accounts, then stops.",
        "Odoo's dynamic reports are Enterprise, so a Community user who has to file "
        "accounts or hand something to an auditor has nothing to hand them.",
    ),
    "blocks": [
        {
            "h2": "The three statements",
            "bullets": [
                ("Trial Balance", "opening, movement and closing per account. Income "
                 "and expense accounts show no opening figure, because they reset each "
                 "financial year and a brought-forward number there would be wrong"),
                ("Profit and Loss", "grouped into operating income, other income, cost "
                 "of revenue, operating expenses, depreciation and other expenses"),
                ("Balance Sheet", "as at a date, including the current period's result "
                 "as equity"),
            ],
        },
        {
            "h2": "Why the current result is on the balance sheet",
            "text": [
                "That result is not sitting in an account until the year is closed. "
                "Leave it out and the sheet does not balance, which is the single most "
                "common thing wrong with a hand-built balance sheet.",
                "And if the two sides ever disagree anyway, the report says so in plain "
                "words rather than printing a total that looks authoritative and is not.",
            ],
        },
        {
            "h2": "Filters",
            "table": {
                "head": ["Filter", "Effect"],
                "rows": [
                    ["Date range", "any period, not just the fiscal year"],
                    ["Journal", "leave empty for all"],
                    ["Company", "one at a time, so the figures mean something"],
                    ["Analytic account", "restrict to entries carrying it — the "
                     "donor-report question"],
                    ["Posted entries only", "on by default"],
                ],
            },
        },
        {
            "h2": "Draft entries are labelled, not hidden",
            "text": [
                "Turn posted-only off and the statement includes drafts — and prints "
                "<em>“Includes draft entries. Not suitable for filing.”</em> across it. "
                "A management figure and a filed figure are different things, and a "
                "report that does not say which it is will eventually be filed.",
            ],
        },
    ],
    "footer": "Odoo 19.0 Community · depends on <code>account</code>. Prints through "
              "ordinary QWeb, so it exports to PDF like any other Odoo report.",
}
