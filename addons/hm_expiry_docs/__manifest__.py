# Part of hm_expiry_docs. See LICENSE file for full copyright and licensing details.
{
    "name": "Expiring Documents",
    "summary": "Track anything with an expiry date, and be reminded before "
               "it lapses",
    "description": """
Expiring Documents
==================

Every organisation tracks things that expire -- licences, permits, visas,
insurance, vehicle registrations, professional certifications -- and most
track them in a spreadsheet that nobody opens until something has already
lapsed.

One generic model covers all of them. A work permit and a vehicle
registration are the same shape: a number, a holder, an issue date, an expiry
date and somebody responsible. Six near-identical models would have been six
places to fix the same bug.

**Reminders that reach a person.** Each type sets its own notice period, and
whoever is named responsible gets an ordinary Odoo activity before the
document lapses. Once, not every morning -- a reminder that repeats daily is a
reminder people learn to ignore.

**Renewal keeps the history.** Renewing opens a replacement carrying the
details over, closes the old document, and links the two, so the chain of a
licence over ten years stays intact and searchable.

**Status stays current.** The state is stored so it can be searched and
grouped, and the daily job refreshes it -- otherwise a document saved as valid
would still read valid years after it lapsed.
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
        "views/hm_expiry_document_views.xml",
    ],
    "demo": [
        "demo/hm_expiry_docs_demo.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
