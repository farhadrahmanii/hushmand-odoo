LISTING = {
    "eyebrow": "Purchase",
    "title": "Purchase Requests",
    "lede": "The step before the quotation: a department asks for something, and the "
            "request is checked and approved on its own merits before anyone talks to "
            "a supplier.",
    "callout": (
        "Odoo starts at the request for quotation.",
        "By then somebody has already decided what to buy and from whom. Most "
        "organisations have a step before that, and Community has nothing for it.",
    ),
    "blocks": [
        {
            "h2": "What a request carries",
            "bullets": [
                ("Items, with an estimated cost", "an estimate from the requester — the "
                 "real figure comes from the quotation"),
                ("A budget line", "so the question of whether there is money for it is "
                 "asked at the right moment"),
                ("A written justification", "which is what approvers actually read"),
                ("A suggested vendor, optionally", "a suggestion, not a commitment"),
            ],
        },
        {
            "h2": "A product is optional",
            "text": [
                "A request can describe something that is not in the catalogue yet — "
                "which is usually the case for the things people request. Forcing a "
                "product record first means either a polluted catalogue or a request "
                "nobody raised.",
            ],
        },
        {
            "h2": "Approval is configuration, not code",
            "text": [
                "Routing comes from <strong>Approval Workflows</strong>, so who signs "
                "off, in what order and under what conditions is set up by the customer. "
                "One process can send small requests to a manager and large ones to the "
                "director as well, without a developer.",
            ],
        },
        {
            "h2": "And then it becomes an order",
            "text": [
                "An approved request becomes a quotation in one click, carrying its "
                "items and budget line onto the purchase order — which keeps a link "
                "back to the request, so the order can always be traced to the person "
                "who asked and the approval that allowed it.",
                "Requesters see their own requests and anything they are approving, "
                "which keeps the list useful rather than exhaustive.",
            ],
        },
    ],
    "footer": "Odoo 19.0 Community · depends on <code>purchase</code> and "
              "<code>hm_approvals</code>. <code>af_procurement</code> adds the "
              "comparative form between approval and order.",
}
