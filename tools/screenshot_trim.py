# Part of the Hushmand Odoo addons tooling.
"""Trim the dead space below a screenshot's content.

A browser window is 1000 pixels tall and a list of three rows is not. Left
alone, every listing image is a strip of interface floating above six hundred
pixels of empty grey, which reads as an empty product no matter what the rows
say.

So the background is measured from the bottom edge and rows matching it are
cut, leaving a margin so the result does not look guillotined. Width is never
touched: the columns are the content.

Used at capture time by take_screenshots.py, and runnable on its own over a
directory of PNGs already captured:

    python tools/screenshot_trim.py screenshots/en
"""

import pathlib
import sys

#: Keep this much empty space below the last content row, in pixels.
MARGIN = 28

#: Never crop shorter than this. A nearly-empty screen trimmed to its content
#: becomes a sliver that looks broken rather than sparse.
MINIMUM_HEIGHT = 380

#: How far a pixel may differ from the background and still count as
#: background. Odoo's greys are not perfectly flat once scaled.
TOLERANCE = 6


def content_bottom(image):
    """The last row holding anything other than the background colour."""
    width, height = image.size
    pixels = image.load()

    # Sample the very bottom-left, which is empty on every screen Odoo draws.
    background = pixels[2, height - 3]

    # Step across rather than reading every pixel: a row that holds content
    # holds it in more than one place, and this runs over twenty images.
    for y in range(height - 1, -1, -1):
        for x in range(0, width, 4):
            pixel = pixels[x, y]
            if any(abs(pixel[i] - background[i]) > TOLERANCE for i in range(3)):
                return y
    return height - 1


def trim(path):
    """Crop one PNG in place. Returns (before, after) heights."""
    from PIL import Image

    with Image.open(path) as image:
        image = image.convert("RGB")
        width, height = image.size
        wanted = min(height, max(MINIMUM_HEIGHT, content_bottom(image) + MARGIN))
        if wanted >= height:
            return height, height
        image.crop((0, 0, width, wanted)).save(path)
        return height, wanted


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    directory = pathlib.Path(sys.argv[1])
    images = sorted(directory.glob("*.png"))
    if not images:
        raise SystemExit("No PNGs in %s" % directory)
    for image in images:
        before, after = trim(image)
        print("%-24s %4d -> %4d" % (image.stem, before, after))
    return 0


if __name__ == "__main__":
    sys.exit(main())
