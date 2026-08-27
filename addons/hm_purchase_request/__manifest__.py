# Part of hm_purchase_request. See LICENSE file for full copyright and licensing details.
{
    "name": "Purchase Requests",
    "summary": "The step before the quotation: a department asks, and the "
               "request is approved on its own merits",
    "description": """
Purchase Requests
=================

Odoo starts at the request for quotation, where somebody has already decided
what to buy and from whom. Most organisations have a step before that: a
department asks for something, and the request is checked and approved on its
own merits before anyone talks to a supplier.

Odoo Community has nothing for it. This is that step.

* A request carries items, an estimated cost, a budget line and a written
  justification, which is what approvers actually read.
* Approval routing comes from **Approval Workflows**, so who signs off, in
  what order and under what conditions is configuration rather than code. One
  process can send small requests to a manager and large ones to the director
  as well.
* An approved request becomes a quotation in one click, carrying its items and
  budget line onto the purchase order, which keeps a link back to the request.
* A product is optional. A request can describe something that is not in the
  catalogue yet, which is usually the case for the things people request.

Requesters see their own requests and anything they have been asked to approve.
Purchasing sees everything.
""",
    "version": "19.0.1.0.0",
    "category": "Inventory/Purchase",
    "author": "Farhad Rahmani",
    "website": "https://hushmand.af",
    "license": "OPL-1",
    "depends": ["purchase", "hm_approvals"],
    "data": [
        "security/ir.model.access.csv",
        "security/hm_purchase_request_rules.xml",
        "data/ir_sequence_data.xml",
        "views/hm_purchase_request_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
