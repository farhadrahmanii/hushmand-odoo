LISTING = {
    "eyebrow": "Human Resources",
    "title": "Shift Rosters",
    "lede": "Schedule guards, drivers or a reception desk — and be told when the "
            "roster is broken, at the moment it breaks.",
    "callout": (
        "Odoo Planning is Enterprise.",
        "The usual fallback is a spreadsheet per month, and it always fails the same "
        "two ways: somebody ends up on two shifts at once, or a night nobody is "
        "covering goes unnoticed until it is that night.",
    ),
    "screenshot": "A week's roster, with uncovered shifts counted",
    "blocks": [
        {
            "h2": "Both failures are checked",
            "bullets": [
                ("Double-booking is refused outright", "assigning somebody to "
                 "overlapping shifts raises an error when it happens, rather than being "
                 "discovered on the night"),
                ("Publishing with gaps takes a second, deliberate action", "the normal "
                 "button refuses and says how many shifts are uncovered; a separate one "
                 "publishes anyway, for when the gap is known and accepted"),
            ],
        },
        {
            "h2": "Night shifts are handled properly",
            "text": [
                "A shift from 18:00 to 06:00 ends on the following day. The hours are "
                "real datetimes rather than a pair of clock times that quietly compute "
                "a negative duration — which is the bug every hand-built roster "
                "spreadsheet has.",
            ],
        },
        {
            "h2": "Shift templates",
            "text": [
                "The patterns you use over and over — Day 08:00–16:00, Night "
                "18:00–06:00 — so building a month means choosing a shift and a person "
                "rather than typing times. The hours come from the template and can "
                "still be overridden on the day it matters.",
            ],
        },
        {
            "h2": "Draft, published, closed",
            "table": {
                "head": ["State", "Meaning"],
                "rows": [
                    ["Draft", "being planned; nobody has been told yet"],
                    ["Published", "the roster people are working to"],
                    ["Closed", "finished — and it cannot be reopened, you copy it"],
                ],
            },
        },
    ],
    "footer": "Odoo 19.0 Community · depends on <code>hr</code> and "
              "<code>mail</code>.",
}
