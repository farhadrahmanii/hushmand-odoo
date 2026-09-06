LISTING = {
    "eyebrow": "Human Resources · Localization",
    "title": "Afghanistan HR",
    "lede": "The employee fields an Afghan organisation actually files on: names "
            "without a surname, the tazkira as it really is, addresses two levels "
            "deeper than Odoo goes, and disciplinary actions Odoo has in neither "
            "edition.",
    "callout": (
        "Added where they belong, not bolted on.",
        "These are fields on the employee and the contract version, so they appear in "
        "the ordinary HR screens, export like anything else, and are searchable "
        "without a custom view.",
    ),
    "screenshot": "Disciplinary actions, from a verbal warning closed to a suspension still running",
    "blocks": [
        {
            "h2": "Names that identify a person",
            "text": [
                "Afghan names carry no inherited surname. Someone is identified by "
                "their own name plus their father's and grandfather's, and every "
                "official document is issued that way — <em>s/o</em> and <em>g/o</em> "
                "on the printed card, <bdi>ولد</bdi> and <bdi>بن</bdi> on the Dari "
                "one.",
            ],
        },
        {
            "h2": "The tazkira as it actually is",
            "table": {
                "head": ["Document", "Identified by", "Recorded as"],
                "rows": [
                    ["Paper tazkira", "volume, page and registration entry <em>together"
                     "</em>", "three fields, written the way a clerk reads them"],
                    ["e-Tazkira", "a national identity number", "one field"],
                ],
            },
        },
        {
            "h2": "Why both, and not one",
            "text": [
                "Both are in circulation. Forcing a paper tazkira into a single serial "
                "number loses the only thing that identifies it, and forcing an "
                "e-Tazkira into three fields invents data. So both shapes are recorded, "
                "and the reference reads back as <em>Volume 12, Page 340, Register "
                "1187</em> when that is what the person has.",
            ],
        },
        {
            "h2": "Also included",
            "bullets": [
                ("Addresses to village level", "province, district and village, for "
                 "where someone lives now <em>and</em> where they are from — different "
                 "questions on every Afghan employment file"),
                ("Disciplinary actions", "verbal warning through to termination, with "
                 "issue and acknowledgement tracked <strong>separately</strong>, "
                 "because whether the employee actually saw it is the part that matters "
                 "later"),
                ("A review date", "for probationary warnings, so the decision is taken "
                 "rather than allowed to lapse"),
                ("An employee ID card", "printable, with photo, identity and a return "
                 "address"),
            ],
        },
    ],
    "footer": "Odoo 19.0 Community · depends on <code>hr</code> and "
              "<code>af_l10n_base</code>, which supplies the provinces and districts.",
}
