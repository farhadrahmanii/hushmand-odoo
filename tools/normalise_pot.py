#!/usr/bin/env python
"""Strip the volatile headers Odoo stamps into every exported template.

    python tools/normalise_pot.py

Odoo writes ``POT-Creation-Date`` and ``PO-Revision-Date`` as "now" every time
it exports. Left in place, a freshly generated template differs from the
committed one on every single run, which makes it impossible to ask the only
question worth asking of a template: **has the source text changed since this
was last exported?**

``Project-Id-Version`` is the third: it carries the build date of whatever
``odoo:19`` image CI pulled ("Odoo Server 19.0-20260926"), so the image moving
forward a month failed the comparison with no string having changed.

The dates carry nothing anyway. A template is generated, not authored, and git
already records when it changed and by whom. So they go, and what remains
diffs to nothing unless a translatable string actually moved.

Only ``.pot`` files are touched. A real ``.po`` is written by a translator and
its revision date is theirs.
"""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
ADDONS = ROOT / "addons"

VOLATILE = (
    '"POT-Creation-Date:',
    '"PO-Revision-Date:',
    '"Project-Id-Version:',
)


def normalise(path):
    lines = path.read_text(encoding="utf-8").split("\n")
    kept = [l for l in lines if not l.startswith(VOLATILE)]
    if len(kept) == len(lines):
        return False
    path.write_text("\n".join(kept), encoding="utf-8")
    return True


def main():
    templates = sorted(ADDONS.glob("*/i18n/*.pot"))
    if not templates:
        print("No templates found under addons/*/i18n/. Nothing to normalise.")
        return 0
    changed = sum(normalise(path) for path in templates)
    print("Normalised %d of %d template(s)." % (changed, len(templates)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
