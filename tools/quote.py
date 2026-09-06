#!/usr/bin/env python
"""Quote a customer, for what they will actually need.

    python tools/quote.py af_hr_payroll
    python tools/quote.py --suite hr
    python tools/quote.py af_zakat af_correspondence --customer "Hewad Relief"
    python tools/quote.py --check

A customer asks for one thing and has to be licensed for another. Somebody
buying Afghan payroll needs a licence covering hm_payroll too, because
hm.payslip is declared there and the gate asks for a licence naming the module
that declares the record. Quote the module and you have quoted 300 dollars for
something that licenses 2,100 dollars of software.

So the closure is resolved first and priced second, and the quote shows both:
what was asked for, and what the licence has to cover.

``--check`` looks for arbitrage. A price list where some combination of suites
undercuts the catalogue is a price list a customer will eventually solve.
"""

import argparse
import itertools
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import build_release  # noqa: E402
import pricing  # noqa: E402


def quote_for(modules, suite=None):
    covered = build_release.resolve_dependencies(list(modules))
    if suite and suite in pricing.SUITE_PRICES:
        result = {
            "modules": covered,
            "chargeable": [m for m in covered if pricing.BANDS_OF(m)],
            "list": pricing.list_price(covered),
            "price": pricing.SUITE_PRICES[suite],
            "discount_rate": None,
            "maintenance": None,
        }
    else:
        result = pricing.price_for(covered)
    return pricing.with_maintenance(result)


def render(asked, quote, customer=None, suite=None):
    lines = []
    if customer:
        lines.append("Quotation for %s" % customer)
        lines.append("")
    lines.append("Asked for : %s" % (suite and ("the %s suite" % suite)
                                     or ", ".join(sorted(asked))))

    pulled = sorted(set(quote["modules"]) - set(asked))
    if pulled:
        lines.append("Licence   : %s" % ", ".join(quote["modules"]))
        lines.append("            (%s are needed for the above to work)"
                     % ", ".join(pulled))
    else:
        lines.append("Licence   : %s" % ", ".join(quote["modules"]))

    lines.append("")
    lines.append("  %-14s %d modules, list USD %s"
                 % ("Licensed:", len(quote["chargeable"]), f"{quote['list']:,}"))
    if quote["discount_rate"]:
        lines.append("  %-14s %d%%" % ("Volume:", quote["discount_rate"] * 100))
    lines.append("  %-14s USD %s  one-off" % ("Licence:", f"{quote['price']:,}"))
    lines.append("  %-14s USD %s  per year, optional"
                 % ("Maintenance:", f"{quote['maintenance']:,}"))
    return "\n".join(lines)


def check():
    """Look for a cheaper way to buy the same thing.

    A price list is only coherent if no combination of what is on it beats
    the item that contains them. Customers find these; better to find them
    first.
    """
    problems = []
    complete = pricing.SUITE_PRICES["complete"]
    everything = set(build_release.all_modules())

    named = [s for s in pricing.SUITE_PRICES if s != "complete"]
    for size in range(2, len(named) + 1):
        for combination in itertools.combinations(named, size):
            covered, cost = set(), 0
            for suite in combination:
                wanted = (build_release.SUITES[suite]["modules"]
                          or build_release.all_modules())
                covered |= set(build_release.resolve_dependencies(wanted))
                cost += pricing.SUITE_PRICES[suite]
            if covered == everything and cost < complete:
                problems.append(
                    "%s together cover the whole catalogue for USD %s, "
                    "undercutting complete at USD %s"
                    % (" + ".join(combination), f"{cost:,}", f"{complete:,}")
                )

    # A suite must not cost more than buying its modules ad hoc.
    for suite, price in pricing.SUITE_PRICES.items():
        wanted = (build_release.SUITES[suite]["modules"]
                  or build_release.all_modules())
        ad_hoc = pricing.price_for(
            build_release.resolve_dependencies(wanted)
        )["price"]
        if price > ad_hoc:
            problems.append(
                "the %s suite costs USD %s but its modules bought ad hoc come "
                "to USD %s" % (suite, f"{price:,}", f"{ad_hoc:,}")
            )

    # Every module must have a band, or a quote for it raises mid-conversation.
    for module in build_release.all_modules():
        if module not in pricing.MODULES:
            problems.append("%s has no price band" % module)

    for problem in problems:
        print("::error::%s" % problem)
    if problems:
        return 1
    print("Price list is coherent: no combination undercuts the catalogue, "
          "no suite costs more than its parts, every module is priced.")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("modules", nargs="*")
    parser.add_argument("--suite", choices=sorted(pricing.SUITE_PRICES))
    parser.add_argument("--customer")
    parser.add_argument("--check", action="store_true",
                        help="look for arbitrage in the price list")
    args = parser.parse_args()

    if args.check:
        return check()

    if args.suite:
        asked = (build_release.SUITES[args.suite]["modules"]
                 or build_release.all_modules())
    elif args.modules:
        asked = args.modules
    else:
        parser.error("name some modules, or --suite, or --check")

    print(render(asked, quote_for(asked, args.suite), args.customer, args.suite))
    return 0


if __name__ == "__main__":
    sys.exit(main())
