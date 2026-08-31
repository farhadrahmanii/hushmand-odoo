# Part of af_zakat. See LICENSE file for full copyright and licensing details.
{
    "name": "Zakat Administration",
    "summary": "Collect, hold and distribute zakat, with a record that "
               "reconciles",
    "description": """
Zakat Administration
====================

Zakat is not an expense. It is an obligation calculated on wealth, collected
into a fund, and distributed to people who qualify under defined categories.
An organisation administering it has to be able to show what came in, who
received what, and that the two reconcile.

Odoo has no concept of any of this, and recording it as ordinary expenses
loses the part that matters: the link between what was collected and what it
paid for.

Two rules the software enforces
-------------------------------

**Nothing is distributed that was never collected.** Marking a distribution as
paid is refused if it exceeds what the fund actually holds. A pledge does not
raise that limit, because a pledge is not money.

**A fund cannot be closed over an undistributed balance.** Zakat collected and
not yet given out is owed to beneficiaries, not held by the organisation, so
closing the books on it is refused until it is distributed or carried forward.

Beneficiaries
-------------

Recorded against the eight categories of eligible recipient, with the
assessment of why they qualify and who verified it. Assistance is totalled
across every fund, so repeat help is visible -- which is what stops the same
households being reached twice while others are missed.

In-kind distributions record what was actually handed over, and each payment
notes whether a receipt was signed.
""",
    "version": "19.0.1.0.0",
    "category": "Accounting",
    "author": "Farhad Rahmani",
    "website": "https://hushmand.af",
    "license": "OPL-1",
    "depends": ["base", "mail", "af_l10n_base", "hm_license"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/af_zakat_views.xml",
    ],
    "demo": [
        "demo/af_zakat_demo.xml",
    ],
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": True,
    "auto_install": False,
}
