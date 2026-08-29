# Part of hm_frontdesk. See LICENSE file for full copyright and licensing details.
{
    "name": "Front Desk",
    "summary": "Visitor register: who is in the building, and who they came "
               "to see",
    "description": """
Front Desk
==========

Odoo's Frontdesk is Enterprise, so a Community user has nowhere to record who
came into the building. Most offices fall back to a paper book at the desk,
which answers "who is here right now?" only by reading every page.

* **Who is on site**, answerable instantly. That is the question asked during
  a fire drill or an incident, not afterwards.
* **Expected visitors** can be registered in advance and checked in with one
  click when they arrive.
* **The host is notified** the moment their visitor reaches reception.
* **Badge, vehicle and identification** recorded where a security desk needs
  them, along with how many people came in together.

Visitors who are never checked out
----------------------------------

That is a paper book's usual failure, and the reason a register slowly stops
being trusted. A daily job finds anyone still on site from a previous day and
asks their host to confirm when they left.

It does not close them automatically. Inventing a departure time nobody
observed would make the register look tidy and be wrong, which is worse than
a record that admits it does not know.
""",
    "version": "19.0.1.0.0",
    "category": "Productivity",
    "author": "Farhad Rahmani",
    "website": "https://hushmand.af",
    "license": "OPL-1",
    "depends": ["base", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/hm_visitor_views.xml",
    ],
    "demo": [
        "demo/hm_frontdesk_demo.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
