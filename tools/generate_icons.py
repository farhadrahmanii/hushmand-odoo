#!/usr/bin/env python3
"""Generate the module icons.

Every Odoo module shows a tile in the Apps list, and an application module
also shows one in the app switcher. Without ``static/description/icon.png``
Odoo falls back to a generic placeholder, which is the first thing a paying
customer sees.

The marks are deliberately plain: a two-letter monogram on a flat tile. The
palette carries the one piece of information worth encoding, which is the
product line -- ``af_`` modules are warm, ``hm_`` modules are cool -- so the
Apps list shows at a glance which tiles are the Afghanistan localization and
which are the horizontal modules that sell anywhere.

Run this after adding a module. The PNGs are committed; this script exists so
they can be regenerated consistently rather than redrawn by hand.
"""

import argparse
import ast
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

SIZE = 140
SUPERSAMPLE = 4
RADIUS_RATIO = 0.22

# The wide image Odoo shows at the top of a module page.
BANNER_WIDTH = 1200
BANNER_HEIGHT = 600

# Warm for the Afghanistan localization, cool for the horizontal modules.
ICONS = {
    "af_correspondence":   ("CR", "#B23A2E"),
    "af_dual_currency":    ("FX", "#C4761B"),
    "af_hr":               ("HR", "#8E442A"),
    "af_hr_payroll":       ("PT", "#A85C1F"),
    "af_jalali":           ("JL", "#A03050"),
    "af_l10n_account":     ("AC", "#7A5C1E"),
    "af_l10n_base":        ("AF", "#6B3F2A"),
    "af_liaison":          ("LN", "#B2542E"),
    "af_procurement":      ("CF", "#97431F"),
    "af_zakat":            ("ZK", "#6E7B22"),
    "hm_account_reports":  ("RP", "#1F5F8B"),
    "hm_approvals":        ("AP", "#2E5A9E"),
    "hm_assets":           ("AS", "#1F6E63"),
    "hm_contracts":        ("CT", "#3B4E8C"),
    "hm_expiry_docs":      ("EX", "#2A6E8F"),
    "hm_frontdesk":        ("FD", "#4A5FA5"),
    "hm_license":          ("LC", "#2D4A73"),
    "hm_payroll":          ("PY", "#1E6B4A"),
    "hm_purchase_request": ("PR", "#26707E"),
    "hm_roster":           ("RS", "#504A9E"),
    "hm_timesheet":        ("TS", "#3E7CB1"),
}

FONT_CANDIDATES = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]


def _font(px):
    for path in FONT_CANDIDATES:
        if pathlib.Path(path).is_file():
            return ImageFont.truetype(path, px)
    raise SystemExit(
        "No bold sans font found. Add one to FONT_CANDIDATES; the icons are "
        "committed, so this only matters when regenerating them."
    )


def _rgb(hex_colour):
    hex_colour = hex_colour.lstrip("#")
    return tuple(int(hex_colour[i:i + 2], 16) for i in (0, 2, 4))


def _lighten(rgb, factor):
    return tuple(min(255, int(c + (255 - c) * factor)) for c in rgb)


def draw_icon(monogram, colour):
    """A flat tile with a soft vertical gradient and a centred monogram."""
    side = SIZE * SUPERSAMPLE
    base = _rgb(colour)

    # Gradient painted row by row, then clipped to the rounded rect by mask.
    gradient = Image.new("RGB", (side, side))
    pen = ImageDraw.Draw(gradient)
    top = _lighten(base, 0.18)
    for y in range(side):
        t = y / (side - 1)
        pen.line(
            [(0, y), (side, y)],
            fill=tuple(int(top[i] + (base[i] - top[i]) * t) for i in range(3)),
        )

    mask = Image.new("L", (side, side), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [(0, 0), (side - 1, side - 1)],
        radius=int(side * RADIUS_RATIO),
        fill=255,
    )

    tile = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    tile.paste(gradient, (0, 0), mask)

    font = _font(int(side * 0.40))
    pen = ImageDraw.Draw(tile)
    left, top_, right, bottom = pen.textbbox((0, 0), monogram, font=font)
    pen.text(
        ((side - (right - left)) / 2 - left,
         (side - (bottom - top_)) / 2 - top_),
        monogram,
        font=font,
        fill=(255, 255, 255, 242),
    )

    return tile.resize((SIZE, SIZE), Image.LANCZOS)


def _wrap(pen, text, font, max_width):
    """Break text to fit a pixel width. PIL will not do this for us."""
    lines = []
    line = []
    for word in text.split():
        candidate = " ".join(line + [word])
        if line and pen.textlength(candidate, font=font) > max_width:
            lines.append(" ".join(line))
            line = [word]
        else:
            line.append(word)
    if line:
        lines.append(" ".join(line))
    return lines


def draw_banner(module, monogram, colour, title, summary):
    """The wide image Odoo shows at the top of a module's page.

    Same palette as the icon, so a customer who saw the tile in the Apps list
    recognises the page it opens. The monogram is repeated as a watermark
    rather than a second tile: at this size a tile reads as a logo, and this
    product does not have one.
    """
    base = _rgb(colour)
    canvas = Image.new("RGB", (BANNER_WIDTH, BANNER_HEIGHT))
    pen = ImageDraw.Draw(canvas)

    top = _lighten(base, 0.22)
    bottom = tuple(int(c * 0.72) for c in base)
    for y in range(BANNER_HEIGHT):
        t = y / (BANNER_HEIGHT - 1)
        pen.line(
            [(0, y), (BANNER_WIDTH, y)],
            fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)),
        )

    margin = int(BANNER_WIDTH * 0.07)
    text_width = int(BANNER_WIDTH * 0.62)

    # Watermark monogram, measured and placed rather than guessed. Sized by
    # eye it bleeds off the edge and reads as a single letter -- which looks
    # like a mistake, not a treatment.
    mark_font = _font(int(BANNER_HEIGHT * 0.62))
    mark = Image.new("RGBA", (BANNER_WIDTH, BANNER_HEIGHT), (0, 0, 0, 0))
    mark_pen = ImageDraw.Draw(mark)
    left, top_, right, bottom = mark_pen.textbbox((0, 0), monogram, font=mark_font)
    mark_pen.text(
        (BANNER_WIDTH - margin - (right - left) - left,
         (BANNER_HEIGHT - (bottom - top_)) / 2 - top_),
        monogram, font=mark_font, fill=(255, 255, 255, 30),
    )
    canvas = Image.alpha_composite(canvas.convert("RGBA"), mark).convert("RGB")
    pen = ImageDraw.Draw(canvas)

    title_font = _font(int(BANNER_HEIGHT * 0.115))
    summary_font = _font(int(BANNER_HEIGHT * 0.048))
    foot_font = _font(int(BANNER_HEIGHT * 0.036))

    title_lines = _wrap(pen, title, title_font, text_width)
    summary_lines = _wrap(pen, summary, summary_font, text_width)[:3]

    title_step = int(BANNER_HEIGHT * 0.135)
    summary_step = int(BANNER_HEIGHT * 0.068)
    rule_y = BANNER_HEIGHT - int(BANNER_HEIGHT * 0.135)

    # Centre the text in the space above the rule, not in the whole canvas:
    # the footer strip is not empty space and centring against it leaves a
    # dead band the eye reads as a mistake.
    block = len(title_lines) * title_step + 24 + len(summary_lines) * summary_step
    y = (rule_y - block) / 2

    for line in title_lines:
        pen.text((margin, y), line, font=title_font, fill=(255, 255, 255))
        y += title_step
    y += 24
    for line in summary_lines:
        pen.text((margin, y), line, font=summary_font, fill=_lighten(base, 0.86))
        y += summary_step

    pen.line([(margin, rule_y), (BANNER_WIDTH - margin, rule_y)],
             fill=_lighten(base, 0.35), width=2)
    line_label = ("Afghanistan localization" if module.startswith("af_")
                  else "For every Odoo Community user")
    pen.text((margin, rule_y + int(BANNER_HEIGHT * 0.038)),
             "Odoo 19.0  ·  %s" % line_label,
             font=foot_font, fill=_lighten(base, 0.72))
    return canvas


def read_manifest(path):
    text = path.read_text(encoding="utf-8")
    return ast.literal_eval(text[text.index("{"):text.rindex("}") + 1])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--icons-only", action="store_true",
                        help="skip the banners")
    parser.add_argument("--banners-only", action="store_true",
                        help="skip the icons")
    args = parser.parse_args()

    addons = pathlib.Path(__file__).resolve().parent.parent / "addons"
    present = {p.name for p in addons.iterdir() if p.is_dir()}

    missing = present - set(ICONS)
    if missing:
        print("::error::modules with no icon defined: %s"
              % ", ".join(sorted(missing)))
        return 1

    for module, (monogram, colour) in sorted(ICONS.items()):
        if module not in present:
            continue
        target = addons / module / "static" / "description"
        target.mkdir(parents=True, exist_ok=True)

        if not args.banners_only:
            draw_icon(monogram, colour).save(target / "icon.png")
        if not args.icons_only:
            manifest = read_manifest(addons / module / "__manifest__.py")
            draw_banner(module, monogram, colour,
                        manifest.get("name", module),
                        manifest.get("summary", "")).save(target / "banner.png")
        print("%-22s %s  %s" % (module, monogram, colour))

    what = ("icons" if args.icons_only
            else "banners" if args.banners_only else "icons and banners")
    print("\n%d %s written" % (len(present), what))
    return 0


if __name__ == "__main__":
    sys.exit(main())
