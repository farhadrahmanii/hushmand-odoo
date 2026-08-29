# Part of af_procurement. See LICENSE file for full copyright and licensing details.
{
    "name": "Afghanistan Procurement",
    "summary": "The comparative form: which suppliers were asked, what each "
               "quoted, and why the chosen one was chosen",
    "description": """
Afghanistan Procurement
=======================

The chain an Afghan office runs is a purchase request, then quotations
compared on a comparative form, then a purchase order, then a goods received
note. Odoo has the middle of that. What it has no concept of at all is the
**comparative form**.

That sheet is the audit trail. A donor or an auditor asking "why this
supplier" is asking for exactly this document, and in most offices it lives in
a folder rather than in the system, which is why it is so often missing when
somebody finally asks.

Two rules, and both exist because of that question
--------------------------------------------------

**A comparison needs at least two quotations.** With one, nothing has been
compared, and calling the sheet a comparison would be a lie on the file.

**Choosing anyone other than the cheapest requires a written reason.** Not
optionally, and not later. The module refuses to complete the form without
it — because that sentence is trivial to write on the day and close to
impossible to reconstruct a year afterwards, which is when it gets asked for.

Delivery time, warranty and payment terms are recorded alongside price, since
those are usually the honest reason a dearer quotation was the right choice.

The decision is posted to the purchase request as well as the form, so the
reasoning sits on the document people actually open.
""",
    "version": "19.0.1.0.0",
    "category": "Inventory/Purchase",
    "author": "Farhad Rahmani",
    "website": "https://hushmand.af",
    "license": "OPL-1",
    "depends": ["hm_purchase_request"],
    "data": [
        "security/ir.model.access.csv",
        "data/af_procurement_data.xml",
        "views/af_comparative_views.xml",
    ],
    "demo": [
        "demo/af_procurement_demo.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
