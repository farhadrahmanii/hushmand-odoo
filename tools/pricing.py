# Part of the Hushmand Odoo addons tooling.
"""The price list, as data.

Prices live here and nowhere else. A number repeated in a document, a
spreadsheet and an email is three numbers that will disagree within a quarter,
and the one the customer remembers is whichever was lowest.

Everything is USD, one-off, per customer, unlimited users unless the licence
says otherwise. Annual maintenance is optional and priced as a percentage of
the licence.

Decided 2026-09-06. See ``docs/PRICING.md`` for the reasoning.
"""

#: One-off licence price by band.
BANDS = {
    "A": 600,   # engines with no equivalent anywhere
    "B": 400,   # replacements for an Enterprise app
    "C": 300,   # Afghan specifics
    "D": 300,   # supporting modules
}

#: Which band each module sits in. hm_license is infrastructure: it is in
#: every licence by necessity and is never a line on an invoice.
MODULES = {
    "hm_payroll": "A",
    "hm_approvals": "A",
    "af_jalali": "A",

    "hm_assets": "B",
    "hm_timesheet": "B",
    "hm_contracts": "B",
    "hm_account_reports": "B",
    "hm_roster": "B",
    "hm_frontdesk": "B",

    "af_hr": "C",
    "af_hr_payroll": "C",
    "af_dual_currency": "C",
    "af_zakat": "C",
    "af_procurement": "C",
    "af_correspondence": "C",
    "af_l10n_base": "C",
    "af_l10n_account": "C",
    "af_liaison": "C",

    "hm_expiry_docs": "D",
    "hm_purchase_request": "D",

    "hm_license": None,
}

#: Suites, priced as a decision rather than computed. A bundle is worth what
#: it is worth to the buyer, not what its parts add up to.
SUITE_PRICES = {
    "hr": 1800,
    "finance": 1500,
    "office": 1600,
    # 3,600 was the intent -- priced near complete so that the four Line B
    # modules it drags in are paid for rather than given away. But its fifteen
    # modules bought ad hoc come to 3,400, so at 3,600 the suite cost more
    # than not buying the suite, and a customer would have found that. 3,300
    # keeps the intent (66% of the catalogue price for 71% of the modules)
    # and is the cheapest way to buy them, which is what a bundle is for.
    "afghanistan": 3300,
    "complete": 5000,
}

#: Volume discount for a set of modules that is not one of the named suites.
#: Steps rather than a curve, because a quote a customer cannot reproduce on
#: the back of an envelope is a quote they will argue with.
VOLUME_DISCOUNT = [
    (1, 0.00),
    (2, 0.10),
    (4, 0.20),
    (7, 0.28),
    (11, 0.33),
]

#: Annual maintenance, as a share of the licence price. Optional, and not
#: sold in year one -- see docs/PRICING.md.
MAINTENANCE_RATE = 0.20


def list_price(modules):
    """What the modules come to before any discount."""
    return sum(BANDS[BANDS_OF(m)] for m in modules if BANDS_OF(m))


def BANDS_OF(module):  # noqa: N802 - reads as a lookup at the call site
    if module not in MODULES:
        raise KeyError(
            "%s has no price band. Add it to tools/pricing.py." % module
        )
    return MODULES[module]


def discount_for(count):
    rate = 0.0
    for threshold, value in VOLUME_DISCOUNT:
        if count >= threshold:
            rate = value
    return rate


def price_for(modules):
    """Price a set of modules, discounted by how many there are."""
    chargeable = [m for m in modules if BANDS_OF(m)]
    gross = list_price(chargeable)
    rate = discount_for(len(chargeable))
    return {
        "modules": sorted(modules),
        "chargeable": sorted(chargeable),
        "list": gross,
        "discount_rate": rate,
        "price": round(gross * (1 - rate) / 50) * 50,  # to the nearest 50
        "maintenance": None,
    }


def with_maintenance(quote):
    quote["maintenance"] = round(quote["price"] * MAINTENANCE_RATE / 50) * 50
    return quote
