LISTING = {
    "eyebrow": "Accounting",
    "title": "Fixed Assets for Odoo Community",
    "lede": "An asset register and a depreciation schedule that posts to the ledger — "
            "when you tell it to, never on its own.",
    "callout": (
        "Without this, a vehicle you buy stays on the balance sheet at full value "
        "forever.",
        "Odoo's asset management is Enterprise. A Community user who buys a vehicle "
        "has a bill and nothing else: no register, no depreciation, and a balance "
        "sheet that overstates what the company owns for the rest of the asset's life.",
    ),
    "blocks": [
        {
            "h2": "The schedule",
            "table": {
                "head": ["Option", "Choices"],
                "rows": [
                    ["Method", "straight line, reducing balance"],
                    ["Frequency", "monthly, quarterly, yearly"],
                    ["First period", "prorated from the in-service date, or a full "
                     "period"],
                    ["Salvage value", "never depreciated past"],
                ],
            },
        },
        {
            "h2": "Nothing posts by itself",
            "text": [
                "The schedule is a forecast until somebody confirms a period. There is "
                "no cron quietly writing entries into a month that has been closed.",
                "Recomputing leaves posted periods untouched and reschedules only what "
                "is left. A posted period cannot afterwards be edited or deleted — to "
                "change it you reverse its journal entry, so the ledger keeps a record "
                "of both.",
            ],
        },
        {
            "h2": "Categories carry the defaults",
            "text": [
                "The method, the number of years and the three accounts live on the "
                "category, so recording a vehicle takes one screen rather than four "
                "decisions. Changing a category later does not reach back and alter "
                "assets that already exist — which is what you want, and not what a "
                "related field would have done.",
            ],
        },
        {
            "h2": "What you can see",
            "bullets": [
                ("Depreciated so far, and the remaining book value", "on the asset, "
                 "without opening the schedule"),
                ("Periods due now", "a filter for the month-end run"),
                ("Unposted periods flagged", "so an asset that has quietly stopped "
                 "being depreciated is visible"),
                ("Closing tells you the book value it closed at", "and refuses to lose "
                 "posted entries on the way"),
            ],
        },
    ],
    "footer": "Odoo 19.0 Community · depends on <code>account</code>. Pairs with the "
              "asset and accumulated-depreciation accounts in "
              "<code>af_l10n_account</code>.",
}
