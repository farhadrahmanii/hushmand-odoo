# Part of hm_approvals. See LICENSE file for full copyright and licensing details.
{
    "name": "Approval Workflows",
    "summary": "Route any document through a configurable multi-step approval "
               "chain, with conditions and dynamic approvers",
    "description": """
Approval Workflows
==================

Odoo Community has no approval engine at all. Enterprise has an Approvals app,
but it models a *request for something* -- a standalone record somebody raises.
It does not put an approval chain in front of a document you already have,
which is what an organisation actually needs.

This does. Pick a document, define the steps, say who approves each one.

**Any document.** Purchase requests, leave, contracts, expenses, a custom
model of your own. A developer adds one mixin; the customer configures the
steps afterwards without touching code.

**Conditional steps.** A step can carry a condition, and is skipped when it
does not hold. One process can therefore say that anything over 50,000 also
needs the director, without a second process to maintain.

**Approvers the document decides.** Instead of naming a person, a step can
name a path -- ``employee_id.parent_id.user_id``, ``project_id.user_id`` --
so the right approver is found from the document itself and the process does
not need rewriting when people change roles.

**Group steps.** Assign a step to a group and everyone in it is notified.
Whoever acts first decides it, and the rest are withdrawn.

**It lands in Odoo's inbox.** Approvers get a normal Odoo activity on the
document, and every decision is posted to the document's chatter, so the
record of who approved what lives where people look for it.

Conditions are a fixed set of operators, not an expression to evaluate.
Configuration that can run arbitrary code is a security problem waiting to
happen.

For developers
--------------

::

    class PurchaseRequest(models.Model):
        _name = "purchase.request"
        _inherit = ["purchase.request", "hm.approval.mixin"]

        def _on_approval_approved(self, request):
            self.state = "approved"

That is the whole integration.
""",
    "version": "19.0.1.0.0",
    "category": "Productivity",
    "author": "Farhad Rahmani",
    "website": "https://hushmand.af",
    "license": "OPL-1",
    "depends": ["base", "mail", "hm_license"],
    "data": [
        "security/hm_approvals_groups.xml",
        "security/ir.model.access.csv",
        "views/hm_approval_views.xml",
    ],
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": True,
    "auto_install": False,
}
