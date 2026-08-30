# Part of hm_contracts. See LICENSE file for full copyright and licensing details.
{
    "name": "Service Contracts",
    "summary": "Recurring contracts that know when they are due, without "
               "billing anyone behind your back",
    "description": """
Service Contracts
=================

Odoo Subscriptions is Enterprise. A Community user with a maintenance
agreement, a security contract or an office lease has an invoice they remember
to raise, or forget to.

A contract records its term, its billing cycle and what it covers, then knows
when the next invoice is due. It also annualises the value, so contracts
billed monthly and yearly can be compared against each other.

Nothing is billed automatically
-------------------------------

The daily job refreshes statuses, raises renewal reminders and flags what is
due -- and stops there. It never raises an invoice on its own.

That is deliberate. Recurring billing that invoices silently is how a customer
receives a bill for a service that stopped three months ago, and how a
supplier relationship ends. Somebody presses the button, and what they get is
a **draft** to check before it is posted.

Also included
-------------

* **Renewal reminders** a notice period before the end date, so the decision
  is made in time rather than discovered late. Contracts marked to renew
  automatically extend instead of asking.
* **Supplier contracts** as well as customer ones. Both are worth tracking;
  only one produces invoices.
* Every invoice keeps a link back to the contract that produced it.
""",
    "version": "19.0.1.0.0",
    "category": "Accounting",
    "author": "Farhad Rahmani",
    "website": "https://hushmand.af",
    "license": "OPL-1",
    "depends": ["account", "hm_license"],
    "data": [
        "security/ir.model.access.csv",
        "data/contract_data.xml",
        "views/hm_contract_views.xml",
    ],
    "demo": [
        "demo/hm_contracts_demo.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
