#!/usr/bin/env python
"""Render the App Store listing page for every module.

    python tools/build_listing.py            # write all of them
    python tools/build_listing.py hm_payroll # just one
    python tools/build_listing.py --check    # fail if any is out of date

Why these are generated
-----------------------

A listing page is the storefront. Twenty of them hand-written means twenty
slightly different greens, four heading sizes and a table that only lines up
on one page — and a customer comparing two modules sees a catalogue assembled
by different people. The chrome is identical by construction here, and
restyling all twenty is one edit to this file.

Odoo embeds the page in its own module view, so there is no stylesheet to link
and every rule is inline. That is the format's constraint, not a choice.

The copy lives in ``tools/listings/<module>.py`` as a ``LISTING`` dictionary.
Strings may contain inline HTML -- ``<strong>``, ``<code>``, ``<em>`` -- and
are written out as-is, so write ``&amp;`` where you mean an ampersand.
"""

import argparse
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
ADDONS = ROOT / "addons"
LISTING_DIR = pathlib.Path(__file__).resolve().parent / "listings"

# One palette for the catalogue. Changing it here changes every page.
INK = "#2b3a34"
MUTED = "#4c5a55"
FAINT = "#75837d"
ACCENT = "#0b6b57"
PANEL = "#f6f7f5"
RULE = "#dce1db"
HAIRLINE = "#eef1ed"
HEAD_BG = "#edf0ec"

FONT = "Roboto,Helvetica,Arial,sans-serif"


def load(module):
    path = LISTING_DIR / ("%s.py" % module)
    if not path.is_file():
        raise SystemExit("No listing copy at %s" % path)
    spec = importlib.util.spec_from_file_location("listing_%s" % module, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded.LISTING


def render_bullets(items):
    out = ['<ul style="font-size:16px;line-height:1.7;color:%s;margin:0 0 30px;'
           'padding-left:20px;">' % MUTED]
    for item in items:
        if isinstance(item, tuple):
            lead, rest = item
            out.append("  <li><strong>%s</strong> — %s</li>" % (lead, rest))
        else:
            out.append("  <li>%s</li>" % item)
    out.append("</ul>")
    return out


def render_table(table):
    cell = "padding:9px 14px;border-bottom:1px solid %s;" % HAIRLINE
    head = "text-align:left;padding:10px 14px;border-bottom:1px solid %s;" % RULE
    out = ['<table style="width:100%;border-collapse:collapse;margin:0 0 30px;'
           'font-size:15px;">',
           '  <thead><tr style="background:%s;">' % HEAD_BG]
    for column in table["head"]:
        out.append('    <th style="%s">%s</th>' % (head, column))
    out.append("  </tr></thead>")
    out.append("  <tbody>")
    for row in table["rows"]:
        cells = "".join('<td style="%s">%s</td>' % (cell, value) for value in row)
        out.append("    <tr>%s</tr>" % cells)
    out.append("  </tbody>")
    out.append("</table>")
    return out


def render_block(block):
    out = []
    if block.get("h2"):
        out.append('<h2 style="font-size:24px;margin:0 0 16px;font-weight:600;">'
                   "%s</h2>" % block["h2"])
    for paragraph in block.get("text", []):
        out.append('<p style="font-size:16px;line-height:1.65;color:%s;'
                   'margin:0 0 14px;">%s</p>' % (MUTED, paragraph))
    if block.get("bullets"):
        out.extend(render_bullets(block["bullets"]))
    if block.get("table"):
        out.extend(render_table(block["table"]))
    if not block.get("bullets") and not block.get("table") and out:
        # Paragraph-only blocks carry their own bottom margin on the last one.
        out[-1] = out[-1].replace("margin:0 0 14px;", "margin:0 0 30px;")
    return out


def render(listing):
    out = [
        '<section style="padding:32px 0;font-family:%s;color:%s;">' % (FONT, INK),
        '  <div style="max-width:900px;margin:0 auto;padding:0 24px;">',
        "",
        '    <p style="font-size:12px;letter-spacing:.14em;text-transform:uppercase;'
        'color:%s;font-weight:600;margin:0 0 10px;">%s</p>' % (
            ACCENT, listing["eyebrow"]),
        '    <h1 style="font-size:40px;line-height:1.1;margin:0 0 14px;'
        'font-weight:700;">%s</h1>' % listing["title"],
        '    <p style="font-size:19px;line-height:1.55;color:%s;max-width:640px;'
        'margin:0 0 28px;">%s</p>' % (MUTED, listing["lede"]),
        "",
    ]

    if listing.get("callout"):
        lead, rest = listing["callout"]
        out += [
            '    <div style="background:%s;border-left:3px solid %s;'
            'padding:18px 22px;margin:0 0 32px;font-size:16px;line-height:1.6;">'
            "<strong>%s</strong> %s</div>" % (PANEL, ACCENT, lead, rest),
            "",
        ]

    if listing.get("screenshot"):
        # A real screen, early. A customer scrolling a catalogue decides from
        # the picture long before they read the second heading, and prose
        # about an approval chain proves nothing that a photograph of one
        # does not prove better.
        # A div rather than <figure>. Odoo runs this page through
        # html_sanitize before showing it, and a plain div with inline styles
        # is the shape the rest of the catalogue already survives on. The
        # relative src is deliberate: Odoo rewrites any src without "//" or
        # "static/" in it to /<module>/static/description/<src>, so making it
        # absolute here would stop that rewrite and break the image.
        out += [
            '    <div style="margin:0 0 34px;">',
            '      <img src="screenshot.png" alt="%s"'
            ' style="width:100%%;height:auto;display:block;border:1px solid %s;'
            'border-radius:3px;"/>' % (listing["screenshot"], RULE),
            '      <div style="font-size:13px;color:%s;padding-top:8px;">'
            "%s</div>" % (FAINT, listing["screenshot"]),
            "    </div>",
            "",
        ]

    for block in listing.get("blocks", []):
        for line in render_block(block):
            out.append("    " + line)
        out.append("")

    out += [
        '    <div style="border-top:1px solid %s;padding-top:20px;font-size:14px;'
        'color:%s;">%s</div>' % (RULE, FAINT, listing["footer"]),
        "",
        "  </div>",
        "</section>",
        "",
    ]
    return "\n".join(out)


def modules():
    return sorted(p.stem for p in LISTING_DIR.glob("*.py")
                  if not p.stem.startswith("_"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("modules", nargs="*", help="modules to render")
    parser.add_argument("--check", action="store_true",
                        help="report pages that are out of date, write nothing")
    args = parser.parse_args()

    wanted = args.modules or modules()
    stale = []
    for module in wanted:
        target = ADDONS / module / "static" / "description" / "index.html"
        if not (ADDONS / module).is_dir():
            raise SystemExit("%s is not a module" % module)
        page = render(load(module))
        if args.check:
            current = target.read_text(encoding="utf-8") if target.is_file() else None
            if current != page:
                stale.append(module)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")

    if args.check:
        failed = False
        if stale:
            print("::error::listing pages are out of date: %s. Run "
                  "python tools/build_listing.py" % ", ".join(stale))
            failed = True
        # A module with no copy at all ships with no storefront, which is the
        # kind of gap that is only noticed by the customer who went looking.
        uncovered = [p.name for p in sorted(ADDONS.iterdir())
                     if p.is_dir() and p.name not in modules()]
        if not args.modules and uncovered:
            print("::error::no listing copy for: %s. Add "
                  "tools/listings/<module>.py" % ", ".join(uncovered))
            failed = True

        # A page that declares a screenshot and does not have one renders a
        # broken image at the top of the thing a customer is deciding from.
        for module in wanted:
            if not load(module).get("screenshot"):
                continue
            shot = ADDONS / module / "static" / "description" / "screenshot.png"
            if not shot.is_file():
                print("::error::%s declares a screenshot but %s is missing. "
                      "Download the screenshots artifact from the screens job."
                      % (module, shot.relative_to(ROOT)))
                failed = True
        if failed:
            return 1
        print("All %d listing pages are current." % len(wanted))
        return 0

    missing = [p.name for p in sorted(ADDONS.iterdir())
               if p.is_dir() and p.name not in modules()]
    print("Wrote %d listing page(s)." % len(wanted))
    if missing:
        print("No copy yet for: %s" % ", ".join(missing))
    return 0


if __name__ == "__main__":
    sys.exit(main())
