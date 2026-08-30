LISTING = {
    "eyebrow": "Accounting",
    "title": "Zakat Administration",
    "lede": "Collect zakat into a fund, distribute it to people who qualify, and be "
            "able to show that the two reconcile.",
    "callout": (
        "Zakat is not an expense.",
        "It is an obligation calculated on wealth, collected into a fund and "
        "distributed under defined categories. Recording it as ordinary expenses loses "
        "the part that matters: the link between what was collected and what it paid "
        "for.",
    ),
    "blocks": [
        {
            "h2": "Two rules the software enforces",
            "bullets": [
                ("Nothing is distributed that was never collected", "marking a "
                 "distribution as paid is refused if it exceeds what the fund actually "
                 "holds — and a pledge does not raise that limit, because a pledge is "
                 "not money"),
                ("A fund cannot be closed over an undistributed balance", "zakat "
                 "collected and not yet given out is owed to beneficiaries, not held by "
                 "the organisation, so closing the books on it is refused until it is "
                 "distributed or carried forward"),
            ],
        },
        {
            "h2": "The eight categories",
            "text": [
                # Each Arabic run is isolated: without <bdi> the ASCII commas
                # between right-to-left terms are reordered by the browser and
                # the list reads as nonsense.
                "Beneficiaries are recorded against the eight eligible categories — "
                "<bdi>فقیر</bdi>, <bdi>مسکین</bdi>, <bdi>عامل</bdi>, "
                "<bdi>مؤلفة القلوب</bdi>, <bdi>الرقاب</bdi>, <bdi>غارم</bdi>, "
                "<bdi>فی سبیل الله</bdi>, <bdi>ابن السبیل</bdi> — with the assessment "
                "of why the person qualifies and who verified it, kept on the record "
                "rather than in somebody's memory.",
            ],
        },
        {
            "h2": "So the same households are not reached twice",
            "text": [
                "Each beneficiary carries how many times they have been helped, how "
                "much in total and when they last received something — across "
                "<em>every</em> fund, not just the one in front of you.",
                "That is what stops a well-known family being assisted three times "
                "while a street away somebody is missed, which is the failure that "
                "quietly discredits a distribution programme.",
            ],
        },
        {
            "h2": "The record a donor can be shown",
            "bullets": [
                ("Cash, bank transfer or in kind", "with what was actually handed over "
                 "recorded when it was not money"),
                ("Anonymous contributions", "zakat is often given without the giver "
                 "being named — the record still exists, the name simply is not shown"),
                ("Signed receipts", "tracked, and their absence is searchable"),
                ("Collected, distributed and undistributed", "on the fund, at all "
                 "times, reconciling to each other"),
            ],
        },
    ],
    "footer": "Odoo 19.0 Community · depends on <code>mail</code> and "
              "<code>af_l10n_base</code>.",
}
