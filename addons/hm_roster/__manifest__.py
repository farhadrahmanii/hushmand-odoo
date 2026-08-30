# Part of hm_roster. See LICENSE file for full copyright and licensing details.
{
    "name": "Shift Rosters",
    "summary": "Schedule guards, drivers or a reception desk, and be told "
               "when the roster is broken",
    "description": """
Shift Rosters
=============

Odoo Planning is Enterprise, so a Community user scheduling guards, drivers or
a reception desk has nothing. The usual fallback is a spreadsheet per month,
and it always fails the same two ways: somebody ends up on two shifts at once,
or a night nobody is covering goes unnoticed until it is that night.

Both are checked here.

**Double-booking is refused outright.** Assigning somebody to overlapping
shifts raises an error at the moment it happens, rather than being discovered
on the night.

**Publishing a roster with gaps takes a second, deliberate action.** A roster
with unassigned shifts is exactly what gets published by accident. The normal
button refuses and says how many are uncovered; a separate one publishes
anyway, for when the gap is known and accepted.

**Night shifts are handled properly.** A shift from 18:00 to 06:00 ends on the
following day, so the hours are real datetimes rather than a pair of clock
times that quietly compute a negative duration.

Shift templates carry the common patterns, so building a month is choosing a
shift and a person rather than typing times.
""",
    "version": "19.0.1.0.0",
    "category": "Human Resources",
    "author": "Farhad Rahmani",
    "website": "https://hushmand.af",
    "license": "OPL-1",
    "depends": ["base", "mail", "hr", "hm_license"],
    "data": [
        "security/ir.model.access.csv",
        "views/hm_roster_views.xml",
    ],
    "demo": [
        "demo/hm_roster_demo.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
