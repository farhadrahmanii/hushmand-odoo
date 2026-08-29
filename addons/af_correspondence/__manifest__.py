# Part of af_correspondence. See LICENSE file for full copyright and licensing details.
{
    "name": "Correspondence Register (Maktoob)",
    "summary": "Incoming and outgoing official letters, numbered in order",
    "description": """
Correspondence Register
=======================

Every Afghan office keeps a bound register of official letters: what came in,
what went out, its number, who it was from, and who was given it to deal with.
When a ministry asks what happened to a letter, the register is what gets
consulted.

Odoo has no concept of it, and attaching a scan to a contact loses the part
that matters -- the sequence. Numbers are issued in order, and a gap in the
outgoing numbers is a question somebody has to answer.

* **Two independent series**, incoming and outgoing, the way a paper register
  keeps two books.
* **The letter's own date and reference** recorded separately from the
  register date, because a letter written on the 1st may not arrive until the
  10th.
* **A correspondent who need not be a contact.** A one-off letter from a
  district office does not justify creating a partner record.
* **Assignment and a reply-by date**, because an incoming letter nobody owns
  is a letter nobody answers.
* **Replies link back** to the letter they answer, so a thread stays intact.

The direction cannot be changed once a letter is registered: its number comes
from that series, and a closed letter cannot be cancelled. The register is a
record of what happened, not a scratchpad.
""",
    "version": "19.0.1.0.0",
    "category": "Productivity",
    "author": "Farhad Rahmani",
    "website": "https://hushmand.af",
    "license": "OPL-1",
    "depends": ["base", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/af_correspondence_views.xml",
    ],
    "demo": [
        "demo/af_correspondence_demo.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
