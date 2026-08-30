#!/usr/bin/env python
"""Prove a language reached the database, rather than trusting that it did.

    python tools/check_translations_loaded.py fa_AF /tmp/loaded

Odoo loads ``i18n/<lang>.po`` when a module is installed and the language is
active. If the file will not parse, or the language was never activated, Odoo
logs a line and carries on: the module installs, the tests pass, CI is green,
and every screen is in English forever.

That is the same failure shape as the demo data this repository shipped for
fourteen modules and never once loaded. So the check does not ask whether
anything went wrong. It exports the language back **out** of the database and
asks whether the translations are in there.

One export per module, not one export of everything
---------------------------------------------------

The directory holds ``<module>.po``, each exported on its own. Exporting all
twenty at once emits each shared term only **once** -- "Cancel" is listed
against whichever module the export reached first -- so measuring per-module
coverage against a combined file makes every module that inherits chatter look
half-translated. The first version of this check did exactly that and reported
57% for a catalogue that was fully translated.
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


def translated(path):
    """The source strings that came back with a translation attached."""
    return {
        entry.msgid for entry in po.parse(path)
        if not entry.is_header and entry.msgstr
    }


def committed(language, module):
    path = ADDONS / module / "i18n" / ("%s.po" % language)
    if not path.is_file():
        return set()
    return translated(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("language")
    parser.add_argument("exported", type=pathlib.Path,
                        help="directory of <module>.po exported from the database")
    args = parser.parse_args()

    if not args.exported.is_dir():
        raise SystemExit("No export directory at %s -- the export step did "
                         "not run." % args.exported)

    modules = sorted(
        p.parent.parent.name
        for p in ADDONS.glob("*/i18n/%s.po" % args.language)
    )
    if not modules:
        raise SystemExit("No committed %s.po files to check." % args.language)

    failures = []
    total_shipped = total_loaded = 0
    print("%-24s %8s %8s" % ("module", "shipped", "loaded"))
    for module in modules:
        shipped = committed(args.language, module)
        export = args.exported / ("%s.po" % module)
        if not export.is_file():
            failures.append("%s was never exported back out of the database"
                            % module)
            print("X %-22s %8d %8s" % (module, len(shipped), "-"))
            continue

        got = translated(export)
        missing = shipped - got
        total_shipped += len(shipped)
        total_loaded += len(shipped) - len(missing)

        flag = " "
        if shipped and not got:
            flag = "X"
            failures.append("%s loaded no %s translations at all"
                            % (module, args.language))
        elif len(missing) > len(shipped) * (1 - MINIMUM_SHARE):
            flag = "X"
            failures.append("%s is missing %d of %d %s translations, e.g. %s"
                            % (module, len(missing), len(shipped),
                               args.language,
                               ", ".join(repr(m[:40]) for m in sorted(missing)[:3])))
        print("%s %-22s %8d %8d" % (
            flag, module, len(shipped), len(shipped) - len(missing)))

    print("%-24s %8d %8d" % ("TOTAL", total_shipped, total_loaded))

    if failures:
        for line in failures:
            print("::error::%s" % line)
        return 1
    print("%s is loaded and readable back out of the database." % args.language)
    return 0


if __name__ == "__main__":
    sys.exit(main())
