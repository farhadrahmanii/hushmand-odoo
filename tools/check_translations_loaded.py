#!/usr/bin/env python
"""Prove a language reached the database, rather than trusting that it did.

    python tools/check_translations_loaded.py fa_AF /tmp/fa_AF-loaded.po

Odoo loads ``i18n/<lang>.po`` when a module is installed and the language is
active. If the file will not parse, or the language was never activated, Odoo
logs a line and carries on: the module installs, the tests pass, CI is green,
and every screen is in English forever.

That is the same failure shape as the demo data this repository shipped for
fourteen modules and never once loaded. So the check does not ask whether
anything went wrong. It exports the language back **out** of the database and
asks whether the translations are in there.
"""

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import po  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
ADDONS = ROOT / "addons"

#: How much of what we committed has to come back. Not 100%: Odoo does not
#: store every exported term the same way it exports it, and a gate that cries
#: wolf gets switched off. A module that loaded nothing at all is the failure
#: worth catching, and that is checked exactly.
MINIMUM_SHARE = 0.80


def module_of(entry):
    for comment in entry.comments:
        if comment.startswith("#. module: "):
            return comment[len("#. module: "):].strip()
    return None


def committed_counts(language):
    counts = {}
    for path in sorted(ADDONS.glob("*/i18n/%s.po" % language)):
        module = path.parent.parent.name
        counts[module] = sum(
            1 for e in po.parse(path) if not e.is_header and e.msgstr
        )
    return counts


def loaded_counts(path):
    counts = {}
    for entry in po.parse(path):
        if entry.is_header or not entry.msgstr:
            continue
        module = module_of(entry)
        if module:
            counts[module] = counts.get(module, 0) + 1
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("language")
    parser.add_argument("exported", type=pathlib.Path,
                        help="the .po exported back out of the database")
    args = parser.parse_args()

    if not args.exported.is_file():
        raise SystemExit("No export at %s -- the export step did not run."
                         % args.exported)

    committed = committed_counts(args.language)
    if not committed:
        raise SystemExit("No committed %s.po files to check." % args.language)
    loaded = loaded_counts(args.exported)

    failures = []
    print("%-24s %8s %8s" % ("module", "shipped", "loaded"))
    for module in sorted(committed):
        shipped = committed[module]
        got = loaded.get(module, 0)
        flag = " "
        if shipped and not got:
            flag = "X"
            failures.append("%s loaded no %s translations at all"
                            % (module, args.language))
        elif shipped and got < shipped * MINIMUM_SHARE:
            flag = "X"
            failures.append("%s loaded %d of %d %s translations"
                            % (module, got, shipped, args.language))
        print("%s %-22s %8d %8d" % (flag, module, shipped, got))

    total_shipped = sum(committed.values())
    total_loaded = sum(loaded.get(m, 0) for m in committed)
    print("%-24s %8d %8d" % ("TOTAL", total_shipped, total_loaded))

    if failures:
        for line in failures:
            print("::error::%s" % line)
        return 1
    print("%s is loaded and readable back out of the database." % args.language)
    return 0


if __name__ == "__main__":
    sys.exit(main())
