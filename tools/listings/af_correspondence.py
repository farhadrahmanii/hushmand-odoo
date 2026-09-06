LISTING = {
    "eyebrow": "Productivity · Localization",
    "title": "Correspondence Register (Maktoob)",
    "lede": "What came in, what went out, its number, who it was from and who has to "
            "deal with it. The bound register every Afghan office keeps, in Odoo.",
    "callout": (
        "The sequence is the point.",
        "Attaching a scan to a contact loses it. Numbers are issued in order, and a gap "
        "in the outgoing numbers is a question somebody has to answer.",
    ),
    "screenshot": "The register: incoming and outgoing letters, each numbered in its own series",
    "blocks": [
        {
            "h2": "Two independent series",
            "text": [
                "Incoming and outgoing are numbered separately, the way a paper "
                "register keeps two books. The direction cannot be changed once a "
                "letter is registered, because its number came from that series — you "
                "cancel it and register a new one, which is exactly what happens with "
                "paper.",
            ],
        },
        {
            "h2": "What a register entry holds",
            "table": {
                "head": ["Recorded", "Why separately"],
                "rows": [
                    ["Register number and date",
                     "issued in order, not editable"],
                    ["The letter's own date",
                     "a letter written on the 1st may not arrive until the 10th"],
                    ["Their reference",
                     "the number the other office put on it"],
                    ["Correspondent",
                     "a contact, or free text — a one-off letter from a district office "
                     "does not justify creating a partner record"],
                ],
            },
        },
        {
            "h2": "So a letter is not lost",
            "bullets": [
                ("Assignment", "an incoming letter nobody owns is a letter nobody "
                 "answers"),
                ("A reply-by date", "with overdue letters filterable, before the "
                 "ministry rings"),
                ("Replies link back", "to the letter they answer, so a thread stays "
                 "intact and readable years later"),
                ("The scan attached", "to the register entry, so the letter can always "
                 "be found again"),
            ],
        },
        {
            "h2": "The register is a record",
            "text": [
                "A closed letter cannot be cancelled. What happened, happened — and a "
                "register that can be tidied up afterwards is not a register anybody "
                "can rely on when the question finally comes.",
            ],
        },
    ],
    "footer": "Odoo 19.0 Community · depends on <code>mail</code> only.",
}
