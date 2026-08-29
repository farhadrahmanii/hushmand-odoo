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

import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

SIZE = 140
SUPERSAMPLE = 4
RADIUS_RATIO = 0.22

# Warm for the Afghanistan localization, cool for the horizontal modules.
ICONS = {
    "af_correspondence":   ("CR", "#B23A2E"),
    "af_dual_currency":    ("FX", "#C4761B"),
    "af_hr":               ("HR", "#8E442A"),
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


def main():
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
        draw_icon(monogram, colour).save(target / "icon.png")
        print("%-22s %s  %s" % (module, monogram, colour))

    print("\n%d icons written" % len(present))
    return 0


if __name__ == "__main__":
    sys.exit(main())
