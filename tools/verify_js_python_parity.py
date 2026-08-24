#!/usr/bin/env python
"""Prove the Python and JavaScript Jalali implementations still agree.

The same conversion exists twice: `core/jalali.py` renders dates on reports,
`static/src/js/jalali.js` renders them on screen. If they ever drift, a printed
payslip and the form it came from will show different dates -- a bug nobody
reports until it is embarrassing.

This runs both over every day in a range and diffs the output.

    python tools/verify_js_python_parity.py
    python tools/verify_js_python_parity.py --from 1800 --to 2200

Requires node on PATH. Exits non-zero on any mismatch, so it can gate CI.
"""

import argparse
import datetime
import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
ADDON = ROOT / "addons" / "af_jalali"
JS_SOURCE = ADDON / "static" / "src" / "js" / "jalali.js"

# Patterns exercised on both sides. Add one here whenever formatting changes.
FORMAT_CASES = [
    {"format": "yyyy/MM/dd", "lang": "en", "scheme": "afghan"},
    {"format": "dd MMMM yyyy", "lang": "en", "scheme": "afghan"},
    {"format": "dd MMMM yyyy", "lang": "fa", "scheme": "afghan"},
    {"format": "dd MMMM yyyy", "lang": "ps", "scheme": "afghan"},
    {"format": "dd MMMM yyyy", "lang": "fa", "scheme": "iranian"},
    {"format": "EEEE dd/MM/yy", "lang": "en", "scheme": "afghan"},
    {"format": "'Issued on' dd/MM/yyyy", "lang": "en", "scheme": "afghan"},
]

JS_DRIVER = """
import { toJalali, formatJalali } from './jalali_module.mjs';

const [fromYear, toYear, casesJson] = process.argv.slice(2);
const cases = JSON.parse(casesJson);
const out = [];

let day = new Date(Date.UTC(Number(fromYear), 0, 1));
const end = Date.UTC(Number(toYear), 11, 31);
while (day.getTime() <= end) {
    const y = day.getUTCFullYear();
    const m = day.getUTCMonth() + 1;
    const d = day.getUTCDate();
    const j = toJalali(y, m, d);
    out.push(`${y}-${m}-${d}|${j.jy}-${j.jm}-${j.jd}`);
    day = new Date(day.getTime() + 86400000);
}

// Formatting is checked on a smaller sample: one day a month is plenty to
// catch a token or month-name divergence.
day = new Date(Date.UTC(Number(fromYear), 0, 1));
while (day.getTime() <= end) {
    const value = {
        year: day.getUTCFullYear(),
        month: day.getUTCMonth() + 1,
        day: day.getUTCDate(),
    };
    for (const c of cases) {
        out.push(formatJalali(value, {
            format: c.format, lang: c.lang, scheme: c.scheme,
        }));
    }
    day = new Date(day.getTime() + 28 * 86400000);
}

process.stdout.write(out.join('\\n'));
"""


def _load_python_core():
    """Import the Tier 0 core without triggering the Odoo imports above it."""
    import importlib
    import types

    module = types.ModuleType("af_jalali")
    module.__path__ = [str(ADDON)]
    sys.modules["af_jalali"] = module
    return (
        importlib.import_module("af_jalali.core.jalali"),
        importlib.import_module("af_jalali.core.formats"),
    )


def python_output(from_year, to_year):
    jalali, formats = _load_python_core()
    lines = []

    day = datetime.date(from_year, 1, 1)
    end = datetime.date(to_year, 12, 31)
    step = datetime.timedelta(days=1)
    while day <= end:
        jy, jm, jd = jalali.to_jalali(day.year, day.month, day.day)
        lines.append("%d-%d-%d|%d-%d-%d" % (day.year, day.month, day.day, jy, jm, jd))
        day += step

    day = datetime.date(from_year, 1, 1)
    step = datetime.timedelta(days=28)
    while day <= end:
        for case in FORMAT_CASES:
            lines.append(
                formats.format_jalali(
                    day, case["format"], scheme=case["scheme"], lang=case["lang"]
                )
            )
        day += step

    return lines


def js_output(from_year, to_year):
    if not JS_SOURCE.is_file():
        raise SystemExit("Missing %s" % JS_SOURCE)

    # Strip the Odoo module marker so plain node can import the file.
    source = re.sub(r"^/\*\* @odoo-module \*\*/", "", JS_SOURCE.read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = pathlib.Path(tmp)
        (tmp_path / "jalali_module.mjs").write_text(source, encoding="utf-8")
        driver = tmp_path / "driver.mjs"
        driver.write_text(JS_DRIVER, encoding="utf-8")

        try:
            result = subprocess.run(
                ["node", str(driver), str(from_year), str(to_year),
                 json.dumps(FORMAT_CASES)],
                capture_output=True,
                check=True,
            )
        except FileNotFoundError:
            raise SystemExit("node is not on PATH; cannot verify parity")
        except subprocess.CalledProcessError as exc:
            sys.stderr.write(exc.stderr.decode("utf-8", "replace"))
            raise SystemExit("node failed while running the JavaScript core")

    return result.stdout.decode("utf-8").split("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="from_year", type=int, default=1900)
    parser.add_argument("--to", dest="to_year", type=int, default=2100)
    args = parser.parse_args()

    py = python_output(args.from_year, args.to_year)
    js = js_output(args.from_year, args.to_year)

    if len(py) != len(js):
        print("MISMATCH: python produced %d lines, javascript %d" % (len(py), len(js)))
        return 1

    mismatches = [(i, p, j) for i, (p, j) in enumerate(zip(py, js)) if p != j]
    if mismatches:
        print("MISMATCH: %d of %d comparisons differ" % (len(mismatches), len(py)))
        for index, p, j in mismatches[:10]:
            print("  line %d: python %r != javascript %r" % (index, p, j))
        return 1

    print(
        "OK: %d comparisons identical (%d..%d, %d format patterns)"
        % (len(py), args.from_year, args.to_year, len(FORMAT_CASES))
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
