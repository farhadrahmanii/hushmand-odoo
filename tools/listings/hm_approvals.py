LISTING = {
    "eyebrow": "Productivity",
    "title": "Approval Workflows",
    "lede": "Put a configurable, multi-step approval chain in front of any document "
            "you already have — purchase requests, leave, contracts, expenses, or a "
            "model of your own.",
    "callout": (
        "Enterprise Approvals models a request. This models an approval.",
        "Odoo's app gives you a standalone record somebody raises. It does not put a "
        "chain in front of a document that already exists, which is what an "
        "organisation actually needs.",
    ),
    "screenshot": "The approval queue: what is waiting, and on whom",
    "blocks": [
        {
            "h2": "Who approves a step",
            "table": {
                "head": ["Kind", "You configure", "Good for"],
                "rows": [
                    ["A specific person", "the user", "a named budget holder"],
                    ["Anyone in a group", "the group — first to act decides",
                     "a finance team where any of three can sign"],
                    ["Whoever the document says",
                     "a path, e.g. <code>employee_id.parent_id.user_id</code>",
                     "the requester's own manager, found from the document"],
                ],
            },
        },
        {
            "h2": "Conditions, so one process covers the whole range",
            "text": [
                "A step can carry a condition and is skipped when it does not hold. One "
                "process can therefore say that anything over 50,000 also needs the "
                "director — without a second process to maintain and keep in step with "
                "the first.",
                "Approvers found from the document mean the process does not need "
                "rewriting when people change roles. Promote someone, and the chain "
                "follows.",
            ],
        },
        {
            "h2": "For the people using it",
            "bullets": [
                ("Waiting on Me", "one queue, and the documents also arrive as ordinary "
                 "Odoo activities"),
                ("A reason to reject", "required, and the requester reads it — a "
                 "rejection with no reason is a conversation somebody has to have twice"),
                ("Comments on approval too", "optional per process, for the chains "
                 "where the approver is expected to say something"),
                ("Your own wording on the button", "Verify, Endorse, Certify — whatever "
                 "the organisation calls it"),
            ],
        },
        {
            "h2": "For the developer",
            "text": [
                "Inherit one mixin and the model gains the whole submit-approve-reject "
                "cycle. The steps themselves are configured by the customer at run "
                "time, not written in code — which is the point: the same module serves "
                "an office that needs one signature and one that needs five.",
            ],
        },
    ],
    "footer": "Odoo 19.0 Community · depends on <code>base</code> and "
              "<code>mail</code> only.",
}
