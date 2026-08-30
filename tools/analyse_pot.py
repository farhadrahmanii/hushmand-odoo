#!/usr/bin/env python
"""What is actually in the templates, so translation can be planned.

    python tools/analyse_pot.py             # summary
    python tools/analyse_pot.py --repeated  # the strings shared across modules
    python tools/analyse_pot.py --untranslated fa_AF   # what is still missing
"""

import argparse
import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import po  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
ADDONS = ROOT / "addons"


def templates():
    return sorted(ADDONS.glob("*/i18n/*.pot"))


def terms(path):
    return [e for e in po.parse(path) if not e.is_header]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeated", action="store_true",
                        help="list terms that appear in more than one module")
    parser.add_argument("--untranslated", metavar="LANG",
                        help="report coverage of <lang>.po against the template")
    args = parser.parse_args()

    counter = collections.Counter()
    per_module = {}
    for path in templates():
        module = path.parent.parent.name
        entries = terms(path)
        per_module[module] = entries
        counter.update(e.msgid for e in entries)

    if args.repeated:
        for text, count in counter.most_common():
            if count < 2:
                break
            print("%2d  %s" % (count, text.replace("\n", " ")[:90]))
        return 0

    if args.untranslated:
        total = done = 0
        for module, entries in sorted(per_module.items()):
            path = ADDONS / module / "i18n" / ("%s.po" % args.untranslated)
            translated = {}
            if path.is_file():
                translated = {
                    e.msgid: e.msgstr for e in po.parse(path)
                    if not e.is_header and e.msgstr
                }
            covered = sum(1 for e in entries if translated.get(e.msgid))
            total += len(entries)
            done += covered
            flag = " " if covered == len(entries) else "*"
            print("%s %-24s %4d / %4d" % (flag, module, covered, len(entries)))
        print("%s %-24s %4d / %4d  (%.0f%%)" % (
            " " if done == total else "*", "TOTAL", done, total,
            100.0 * done / total if total else 0))
        return 0

    unique = len(counter)
    total = sum(len(e) for e in per_module.values())
    shared = sum(1 for c in counter.values() if c > 1)
    print("%d entries across %d modules" % (total, len(per_module)))
    print("%d unique strings, %d of them shared by more than one module"
          % (unique, shared))
    print("%d entries are boilerplate repeats"
          % (total - unique))
    formats = sum(1 for path in templates() for e in terms(path)
                  if e.is_python_format())
    print("%d entries carry format placeholders" % formats)
    print()
    for module, entries in sorted(per_module.items()):
        print("  %-24s %4d" % (module, len(entries)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
