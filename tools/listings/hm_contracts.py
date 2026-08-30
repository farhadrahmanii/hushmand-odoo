LISTING = {
    "eyebrow": "Accounting",
    "title": "Service Contracts",
    "lede": "Recurring contracts that know when they are due — a maintenance "
            "agreement, a security contract, an office lease — without billing anyone "
            "behind your back.",
    "callout": (
        "Odoo Subscriptions is Enterprise.",
        "A Community user with a recurring agreement has an invoice they remember to "
        "raise, or forget to.",
    ),
    "blocks": [
        {
            "h2": "Nothing is billed automatically",
            "text": [
                "The daily job refreshes statuses, raises renewal reminders and flags "
                "what is due — and stops there. It never raises an invoice on its own.",
                "That is deliberate. Recurring billing that invoices silently is how a "
                "customer receives a bill for a service that stopped three months ago, "
                "and how a supplier relationship ends. Somebody presses the button, and "
                "what they get is a <strong>draft</strong> to check before it is posted.",
            ],
        },
        {
            "h2": "What a contract knows",
            "bullets": [
                ("Its term and billing cycle", "monthly, quarterly, every six months or "
                 "yearly"),
                ("When the next invoice is due", "so it appears on a list rather than "
                 "in somebody's memory"),
                ("Its annualised value", "so contracts billed monthly and yearly can be "
                 "compared against each other"),
                ("Which direction it runs", "a contract you bill a customer for, or one "
                 "a supplier bills you for — both worth tracking, only one produces "
                 "invoices"),
            ],
        },
        {
            "h2": "Renewals decided in time",
            "text": [
                "A reminder is raised a notice period before the end date, so the "
                "decision to renew or let it lapse is made before the date rather than "
                "discovered after it. Contracts marked to renew automatically extend "
                "themselves by one term instead of expiring.",
            ],
        },
        {
            "h2": "It keeps the record straight",
            "table": {
                "head": ["Action", "Behaviour"],
                "rows": [
                    ["Cancel a contract that has been invoiced",
                     "refused — close it instead, so the invoices keep their contract"],
                    ["Invoice a contract with no lines",
                     "refused, with the reason"],
                    ["Invoice a supplier contract",
                     "refused — it is billed <em>to</em> you"],
                ],
            },
        },
    ],
    "footer": "Odoo 19.0 Community · depends on <code>account</code>.",
}
