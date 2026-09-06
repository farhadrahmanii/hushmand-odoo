LISTING = {
    "eyebrow": "Administration",
    "title": "Licence Keys",
    "lede": "Offline licence verification for commercial Odoo modules. The customer "
            "pastes a signed key, and it is checked on their own machine against the "
            "supplier's public key.",
    "callout": (
        "Nothing is sent anywhere.",
        "There is no licence server to call, nothing to break when a customer's "
        "connection does, and no telemetry leaving their database. That matters where "
        "connectivity is unreliable — and to anyone who would rather their ERP did not "
        "phone home.",
    ),
    "screenshot": "The licence, every field read out of the signed key",
    "blocks": [
        {
            "h2": "Nothing can be edited into it",
            "text": [
                "Raising the user limit by hand breaks the signature and the licence is "
                "refused. Every field on the screen — who it is for, what it covers, "
                "when it expires, how many users — is read out of the signed payload "
                "rather than typed in.",
            ],
        },
        {
            "h2": "What happens when it lapses",
            "table": {
                "head": ["When", "What the customer sees"],
                "rows": [
                    ["30 days before expiry", "a countdown in the corner of the screen"],
                    ["Expiry, and 30 days after",
                     "everything keeps working; the countdown continues"],
                    ["After the grace month",
                     "covered modules stop accepting <strong>new</strong> work"],
                ],
            },
        },
        {
            "h2": "It never stops showing old work",
            "text": [
                "Reading, printing and exporting keep working whatever the licence "
                "says, so every payslip, contract and report already produced stays "
                "available permanently. The data is the customer's.",
                "Holding it hostage would turn a late renewal into a dispute. Refusing "
                "new work is enough pressure, and it is pressure the customer can "
                "relieve by paying.",
            ],
        },
        {
            "h2": "What this is not",
            "text": [
                "It is not DRM, and does not pretend to be. Odoo modules ship as "
                "readable Python, so a determined person can edit the check out — which "
                "is equally true of every paid module on the App Store.",
                "The purpose is to make the licence <em>legible</em>. The customer can "
                "see what they bought, when it lapses and whether they have outgrown "
                "it; the supplier has something concrete to point at. Enforcement is "
                "contractual. This is what keeps honest customers honest and makes a "
                "renewal a conversation rather than an accusation.",
            ],
        },
    ],
    "footer": "Odoo 19.0 Community · depends on <code>mail</code> only. Ed25519 "
              "signatures, verified with the <code>cryptography</code> library that "
              "ships with Odoo.",
}
