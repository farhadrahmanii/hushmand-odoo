LISTING = {
    "eyebrow": "Accounting · Localization",
    "title": "Afghanistan — Accounting",
    "lede": "A chart of accounts and the tax structure for Afghan businesses and "
            "NGOs. Odoo ships 225 fiscal localizations in its two editions. "
            "Afghanistan is not one of them.",
    "callout": (
        "Read this before you file anything.",
        "Afghan tax rates and thresholds change, and enforcement has varied. The rates "
        "here reflect the long-standing Business Receipts Tax and withholding regime, "
        "but confirm them against current Afghanistan Revenue Department guidance "
        "before filing. They are ordinary Odoo taxes and can be edited.",
    ),
    "screenshot": "The Afghan chart of accounts, applied to a company",
    "blocks": [
        {
            "h2": "The chart",
            "bullets": [
                ("Structured for Afghan practice", "businesses and NGOs, rather than a "
                 "generic chart relabelled"),
                ("Dual AFN and USD cash and bank accounts", "because almost every "
                 "organisation operating there runs both"),
                ("Staff advances", "as a real account, since they are a standing "
                 "feature of Afghan payroll"),
                ("Fixed-asset and accumulated-depreciation pairs", "already matched to "
                 "the Fixed Assets module"),
            ],
        },
        {
            "h2": "Taxes",
            "table": {
                "head": ["Tax", "Rates", "Notes"],
                "rows": [
                    ["Business Receipts Tax", "2%, 4%, 10%", "the rate depends on the "
                     "activity"],
                    ["Withholding — contractors", "2% licensed, 7% unlicensed",
                     "separate liability accounts"],
                    ["Withholding — rent", "10%, 15%", "separate liability accounts"],
                ],
            },
        },
        {
            "h2": "Why the withholding accounts are separate",
            "text": [
                "Contractor and rent withholding are filed separately, so they post to "
                "separate liability accounts. Pooling them into one payable makes the "
                "return a reconciliation exercise every month instead of a figure you "
                "can read off the trial balance.",
                "There is no chart of accounts mandated for Afghanistan, so this is a "
                "sound starting point rather than a legal requirement. Edit it to suit "
                "the organisation.",
            ],
        },
    ],
    "footer": "Odoo 19.0 Community · depends on <code>account</code>.",
}
