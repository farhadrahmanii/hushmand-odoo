# Part of hm_license. See LICENSE file for full copyright and licensing details.
{
    "name": "Licence Keys",
    "summary": "Offline licence verification for commercial Odoo modules",
    "description": """
Licence Keys
============

A licence is a small signed document: who it is for, what it covers, when it
expires, how many users. The customer pastes the key, and it is verified on
their own machine against the supplier's public key.

**Nothing is sent anywhere.** There is no licence server to call, nothing to
break when a customer's connection does, and no telemetry leaving their
database. That matters for organisations working where connectivity is
unreliable, and for anyone who would rather their ERP did not phone home.

**Nothing can be edited into it.** Raising the user limit by hand breaks the
signature and the licence is refused. Every field displayed is read out of the
signed payload rather than typed in.

What happens when it lapses
---------------------------

Nothing sudden. A lapsed licence keeps working for a further thirty days, with
a countdown in the corner of the screen throughout. Only after that do the
modules it covers stop accepting **new** work.

They never stop showing old work. Reading, printing and exporting keep working
whatever the licence says, so every payslip, contract and report already
produced stays available permanently. The data is the customer's.

What this is not
----------------

It is not DRM, and does not pretend to be. Odoo modules ship as readable
Python, so a determined person can edit the check out. That is equally true of
every paid module on the Odoo App Store.

The purpose is to make the licence legible. The customer can see what they
bought, when it lapses and whether they have outgrown it; the supplier has
something concrete to point at. Enforcement is contractual. This is what keeps
honest customers honest and makes a renewal a conversation rather than an
accusation.

Issuing licences
----------------

``tools/issue_license.py`` in this repository generates the keypair and signs
licences. The private key never leaves the supplier.
""",
    "version": "19.0.1.0.0",
    "category": "Administration",
    "author": "Farhad Rahmani",
    "website": "https://hushmand.af",
    "license": "OPL-1",
    "depends": ["base", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/hm_license_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "hm_license/static/src/js/license_systray.js",
            "hm_license/static/src/xml/license_systray.xml",
            "hm_license/static/src/scss/license.scss",
        ],
    },
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
