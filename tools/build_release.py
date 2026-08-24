#!/usr/bin/env python
"""Package one module as a customer-ready ZIP.

Customers receive an archive per purchase, never access to this repository.
That matters commercially: a repo token would hand a customer who bought one
module every other module in the catalogue, released or not.

    python tools/build_release.py af_jalali
    python tools/build_release.py af_jalali --out C:\\releases

Produces  dist/af_jalali-19.0.1.0.0.zip  containing a single top-level folder
named after the module, which is the shape both deployment compose files
expect and also what a customer would drop into their addons directory by
hand.

Upload the file anywhere reachable over HTTPS -- your own site, object storage,
a signed link -- and give the customer that URL. The deployment files take it
as MODULE_ARCHIVE_URL.
"""

import argparse
import ast
import pathlib
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
ADDONS = ROOT / "addons"

# Never ship these.
EXCLUDE_DIRS = {"__pycache__", ".git", ".idea", ".vscode", "node_modules"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".pyd", ".log", ".swp"}
EXCLUDE_NAMES = {".DS_Store", "Thumbs.db"}


def read_manifest(module_path):
    manifest_file = module_path / "__manifest__.py"
    if not manifest_file.is_file():
        raise SystemExit("No __manifest__.py in %s" % module_path)
    text = manifest_file.read_text(encoding="utf-8")
    try:
        return ast.literal_eval(text[text.index("{"):text.rindex("}") + 1])
    except (ValueError, SyntaxError) as exc:
        raise SystemExit("Cannot parse %s: %s" % (manifest_file, exc))


def should_include(path):
    if any(part in EXCLUDE_DIRS for part in path.parts):
        return False
    if path.suffix in EXCLUDE_SUFFIXES:
        return False
    return path.name not in EXCLUDE_NAMES


def build(module, out_dir):
    module_path = ADDONS / module
    if not module_path.is_dir():
        available = sorted(p.name for p in ADDONS.iterdir() if p.is_dir())
        raise SystemExit(
            "Module %r not found. Available: %s" % (module, ", ".join(available))
        )

    manifest = read_manifest(module_path)
    version = manifest.get("version", "0.0.0")
    licence = manifest.get("license", "")

    if licence in ("AGPL-3", "GPL-3", "GPL-2"):
        raise SystemExit(
            "Refusing to package %s: its licence is %s, which obliges you to "
            "let customers redistribute it freely. See README.md." % (module, licence)
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    archive = out_dir / ("%s-%s.zip" % (module, version))

    files = sorted(p for p in module_path.rglob("*") if p.is_file() and should_include(p))
    if not files:
        raise SystemExit("Nothing to package in %s" % module_path)

    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            # Store as af_jalali/... so the archive unpacks to one clean folder.
            zf.write(path, pathlib.Path(module) / path.relative_to(module_path))

    size_kb = archive.stat().st_size / 1024
    print("Packaged %s" % module)
    print("  version : %s" % version)
    print("  licence : %s" % licence)
    print("  files   : %d" % len(files))
    print("  size    : %.1f KB" % size_kb)
    print("  archive : %s" % archive)
    print()
    print("Upload it over HTTPS and give the customer the link as")
    print("MODULE_ARCHIVE_URL in the deployment file.")
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module", help="module directory name, e.g. af_jalali")
    parser.add_argument("--out", default=str(ROOT / "dist"), help="output directory")
    args = parser.parse_args()
    build(args.module, pathlib.Path(args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
