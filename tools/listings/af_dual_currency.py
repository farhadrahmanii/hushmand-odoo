LISTING = {
    "eyebrow": "Accounting · Localization",
    "title": "Dual Currency by Exchange Period",
    "lede": "One agreed AFN/USD rate for a whole month, locked once it has been "
            "reported, with document totals shown in both currencies.",
    "callout": (
        "Odoo converts at the nearest daily rate.",
        "That suits a business marking to market every day. It does not suit an "
        "organisation that fixes one rate for a month and uses it for payroll, tax "
        "filings and every document issued in that month.",
    ),
    "screenshot": "One agreed rate per period, and the months before it",
    "blocks": [
        {
            "h2": "Two things the daily rate table cannot do",
            "bullets": [
                ("One agreed rate per period", "define a period, set the rate, confirm "
                 "it — every document dated inside the period uses that rate"),
                ("Rates that stop changing", "closing a period locks the rate, so "
                 "nobody can quietly edit a figure already reported to the ministry"),
            ],
        },
        {
            "h2": "Draft, confirmed, closed",
            "table": {
                "head": ["State", "Rate can change", "Used by documents"],
                "rows": [
                    ["Draft", "yes", "no"],
                    ["Confirmed", "yes, deliberately", "yes"],
                    ["Closed", "no — reopening is a deliberate act that warns you",
                     "yes"],
                ],
            },
        },
        {
            "h2": "It adds governance, it does not replace Odoo",
            "text": [
                "Confirming a period writes an ordinary Odoo currency rate. Invoices, "
                "accounting and every existing report keep working exactly as they did "
                "— the module puts rules on top of Odoo's own mechanism rather than "
                "substituting its own.",
                "The afghani is activated for you. It ships with Odoo but switched off.",
            ],
        },
        {
            "h2": "On documents",
            "bullets": [
                ("A second-currency total", "on invoices and bills, converted at the "
                 "rate agreed for that document's period"),
                ("Zero means nothing was assumed", "if no confirmed period covers the "
                 "date, the total is zero rather than a rate somebody guessed"),
                ("An inverse rate shown alongside", "for checking, because the "
                 "direction of a rate is the easiest thing in accounting to get "
                 "backwards"),
            ],
        },
    ],
    "footer": "Odoo 19.0 Community · depends on <code>account</code> and "
              "<code>base_setup</code>.",
}
