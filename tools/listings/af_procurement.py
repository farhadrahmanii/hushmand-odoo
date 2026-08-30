LISTING = {
    "eyebrow": "Purchase · Localization",
    "title": "The Comparative Form",
    "lede": "Which suppliers were asked, what each quoted, and why the chosen one was "
            "chosen. The document a donor or an auditor asks for — and the one Odoo "
            "has no concept of.",
    "callout": (
        "This sheet is the audit trail.",
        "In most offices it lives in a folder rather than in the system, which is "
        "exactly why it is so often missing when somebody finally asks for it.",
    ),
    "blocks": [
        {
            "h2": "Two rules, and both exist because of that question",
            "bullets": [
                ("A comparison needs at least two quotations", "with one, nothing has "
                 "been compared, and calling the sheet a comparison would be a lie on "
                 "the file"),
                ("Choosing anyone other than the cheapest requires a written reason",
                 "not optionally, and not later — the form will not complete without it"),
            ],
        },
        {
            "h2": "Why the reason is compulsory",
            "text": [
                "That sentence is trivial to write on the day and close to impossible "
                "to reconstruct a year afterwards — which is when it gets asked for.",
                "The module also stores the fact that the chosen quotation was not the "
                "lowest, as a searchable flag. That is what an auditor filters on, and "
                "a filter that cannot be searched is a filter nobody uses.",
            ],
        },
        {
            "h2": "What each quotation records",
            "table": {
                "head": ["Field", "Why it is on the sheet"],
                "rows": [
                    ["Supplier and amount", "the comparison itself"],
                    ["Quotation number and date",
                     "the supplier's own reference, so the paper can be found again"],
                    ["Delivery in days", "often the reason a dearer quotation wins"],
                    ["Warranty in months", "the other common reason"],
                    ["Payment terms", "a cheaper price on worse terms is not cheaper"],
                ],
            },
        },
        {
            "h2": "It ends where Odoo begins",
            "text": [
                "Completing the form sets the supplier on the purchase request, which "
                "then becomes an ordinary Odoo quotation. The chain is: request, "
                "comparison, order — with the comparison kept as the record of how the "
                "middle step was decided.",
            ],
        },
    ],
    "footer": "Odoo 19.0 Community · depends on <code>hm_purchase_request</code>, "
              "which brings <code>purchase</code> and the approval engine with it.",
}
