LISTING = {
    "eyebrow": "Productivity",
    "title": "Expiring Documents",
    "lede": "Licences, permits, visas, insurance, vehicle registrations, professional "
            "certifications — tracked in one place, with a reminder that reaches a "
            "person before the thing lapses.",
    "callout": (
        "Most organisations track these in a spreadsheet.",
        "And nobody opens it until something has already expired. A reminder that "
        "depends on somebody remembering to look is not a reminder.",
    ),
    "blocks": [
        {
            "h2": "One model, not six",
            "text": [
                "A work permit and a vehicle registration are the same shape: a number, "
                "a holder, an issue date, an expiry date and somebody responsible. Six "
                "near-identical models would have been six places to fix the same bug.",
                "Document types carry the differences — how long this kind of document "
                "is normally valid, how much notice you want, and whether it even has a "
                "number. A passport has one; a signed undertaking may not.",
            ],
        },
        {
            "h2": "Reminders that reach a person",
            "bullets": [
                ("An ordinary Odoo activity", "for whoever is named responsible, so it "
                 "appears where they already work"),
                ("Once, not every morning", "a reminder that repeats daily is a "
                 "reminder people learn to ignore"),
                ("Named responsibility", "a document nobody owns is a document nobody "
                 "renews"),
            ],
        },
        {
            "h2": "Renewal keeps the history",
            "text": [
                "Renewing opens a replacement carrying the details over, closes the old "
                "document and links the two — so the chain of a licence over ten years "
                "stays intact and searchable, rather than being one record overwritten "
                "nine times.",
            ],
        },
        {
            "h2": "Status you can search",
            "table": {
                "head": ["Status", "Set by"],
                "rows": [
                    ["Valid, expiring, expired", "the dates, refreshed by the daily job"],
                    ["Renewed", "by hand, when a replacement is issued"],
                    ["Cancelled", "by hand, when a document is withdrawn"],
                ],
            },
        },
        {
            "h2": "Why the status is stored rather than computed",
            "text": [
                "It depends on today. A computed field is calculated when the record is "
                "read, which means it cannot be searched or grouped — and a list of "
                "everything expiring this month is the entire reason for the module. So "
                "it is stored, and a daily job keeps it honest.",
            ],
        },
    ],
    "footer": "Odoo 19.0 Community · depends on <code>mail</code> only. "
              "<code>af_liaison</code> builds the Afghan visa and permit types on top "
              "of it.",
}
