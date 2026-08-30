#!/usr/bin/env python
"""Project a translation memory onto every module template.

    python tools/build_po.py fa_AF            # write addons/*/i18n/fa_AF.po
    python tools/build_po.py fa_AF --harvest  # fold reviewer edits back in
    python tools/build_po.py fa_AF --check    # report, change nothing

Why a memory and not twenty hand-written files
----------------------------------------------

1,911 terms across the catalogue are only 1,246 distinct strings: "Created by",
"Followers", "Company" and their kin repeat in every module that inherits
chatter. Translating those once, in one place, is the difference between a
catalogue that reads as one product and twenty modules that each invented their
own word for "Cancel".

The memory lives in ``tools/translations/<lang>.py`` as a plain dictionary,
which is far quicker to read and diff than the same content wrapped in PO
syntax.

Reviewer edits are never lost
-----------------------------

A translation is a professional judgement, and the reviewer's beats the
memory's. Where a committed ``.po`` already carries a translation that differs
from the memory, the build **keeps the file's version** and says so. Run
``--harvest`` to fold those decisions back into the memory, and every other
module picks up the same wording.
"""

import argparse
import importlib.util
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import po  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
ADDONS = ROOT / "addons"
MEMORY_DIR = pathlib.Path(__file__).resolve().parent / "translations"


def load_memory(language):
    """Return (translations, overrides).

    ``overrides`` is keyed by module, for the terms where one English word
    honestly means two different things. Odoo's translations are keyed by the
    source string alone, with no context, so "Post" is the accounting action in
    hm_assets and a guard's post in hm_roster and nothing in the file format
    can tell them apart. Naming the exceptions is better than letting one of
    them be quietly wrong.
    """
    path = MEMORY_DIR / ("%s.py" % language)
    if not path.is_file():
        raise SystemExit("No translation memory at %s" % path)
    spec = importlib.util.spec_from_file_location("memory_%s" % language, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return (
        module.TRANSLATIONS,
        getattr(module, "OVERRIDES", {}),
        getattr(module, "VERBATIM", set()),
    )


def literal(text):
    """Quote a string for the memory file, keeping the letters readable.

    `repr` renders every zero-width non-joiner as an escape, and Dari uses one
    in almost every plural and compound -- the memory would come out as a wall
    of `\\u200c`. A file nobody can read is a file nobody reviews, so the
    quoting is done by hand and the text stays text.
    """
    escaped = (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\t", "\\t")
    )
    return '"%s"' % escaped


def save_memory(language, translations, header):
    """Rewrite the memory, sorted, so a diff shows only what changed.

    Everything above ``TRANSLATIONS =`` is copied through, which is why
    OVERRIDES and VERBATIM are declared before it: a harvest must not quietly
    drop the decisions recorded there.
    """
    path = MEMORY_DIR / ("%s.py" % language)
    lines = [header.rstrip("\n"), "", "TRANSLATIONS = {"]
    for source in sorted(translations):
        lines.append("    %s: %s," % (
            literal(source), literal(translations[source])))
    lines.append("}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def memory_header(language):
    """Keep everything above ``TRANSLATIONS =`` when rewriting."""
    path = MEMORY_DIR / ("%s.py" % language)
    text = path.read_text(encoding="utf-8")
    return text[:text.index("TRANSLATIONS = {")]


def templates():
    return sorted(ADDONS.glob("*/i18n/*.pot"))


def placeholders_agree(entry, translation):
    """A translation that loses a %(name)s crashes when it is rendered."""
    import re
    pattern = re.compile(r"%(?:\([^)]+\))?[sdfr]")
    return sorted(pattern.findall(entry.msgid)) == sorted(
        pattern.findall(translation)
    )


def build(language, harvest=False, check=False):
    translations, overrides, verbatim = load_memory(language)
    harvested = {}
    reports = []
    written = 0
    total = covered = 0

    for template in templates():
        module = template.parent.parent.name
        target = template.parent / ("%s.po" % language)
        module_overrides = overrides.get(module, {})

        existing = {}
        if target.is_file():
            existing = {
                e.msgid: e.msgstr for e in po.parse(target)
                if not e.is_header and e.msgstr
            }

        entries = [po.header(language, [module])]
        for entry in po.parse(template):
            if entry.is_header:
                continue
            total += 1
            override = module_overrides.get(entry.msgid)
            reviewed = existing.get(entry.msgid)
            remembered = translations.get(entry.msgid)
            # A term that must not change -- a format pattern, a technical
            # name -- is translated to itself, so the file records that
            # somebody looked at it and decided, rather than leaving a blank
            # that reads as unfinished work.
            if entry.msgid in verbatim:
                remembered = entry.msgid
            chosen = override or reviewed or remembered or ""

            # An override is a decision already recorded, so a .po that agrees
            # with it is not a new judgement to harvest.
            if not override:
                if reviewed and remembered and reviewed != remembered:
                    reports.append(
                        "%s: kept the reviewed wording for %r"
                        % (module, entry.msgid[:50])
                    )
                    harvested[entry.msgid] = reviewed
                elif reviewed and not remembered:
                    harvested[entry.msgid] = reviewed

            if chosen and not placeholders_agree(entry, chosen):
                reports.append(
                    "%s: PLACEHOLDER MISMATCH in %r -- dropped" % (module, entry.msgid[:50])
                )
                chosen = ""

            if chosen:
                covered += 1
            entries.append(po.Entry(entry.comments, entry.msgid, chosen))

        if not check:
            po.write(target, entries)
            written += 1

    if harvest and harvested:
        translations.update(harvested)
        save_memory(language, translations, memory_header(language))
        print("Harvested %d reviewed translation(s) into the memory." % len(harvested))

    for line in reports:
        print(line)
    print("%s: %d / %d terms translated (%.0f%%)%s" % (
        language, covered, total, 100.0 * covered / total if total else 0,
        "" if check else ", %d files written" % written,
    ))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("language", help="language code, e.g. fa_AF")
    parser.add_argument("--harvest", action="store_true",
                        help="fold translations found in the .po files back into the memory")
    parser.add_argument("--check", action="store_true",
                        help="report coverage without writing anything")
    args = parser.parse_args()
    return build(args.language, harvest=args.harvest, check=args.check)


if __name__ == "__main__":
    sys.exit(main())
