#!/usr/bin/env python
"""Package modules as customer-ready ZIPs.

    python tools/build_release.py af_jalali             # one module
    python tools/build_release.py af_procurement --with-deps
    python tools/build_release.py --suite hr            # a bundle
    python tools/build_release.py --all                 # every module, separately
    python tools/build_release.py --all --out C:/releases

Customers receive an archive per purchase, never access to this repository.
That matters commercially: a repo token would hand a customer who bought one
module every other module in the catalogue, released or not.

Every archive unpacks to one folder per module, which is the shape both
deployment compose files expect and also what a customer would drop into their
addons directory by hand.

Dependencies are the thing that goes wrong
------------------------------------------

``af_procurement`` needs ``hm_purchase_request``, which needs ``hm_approvals``,
and all of them need ``hm_license``. Ship the one module the customer asked for
and Odoo refuses to install it, at their site, on the day they try. So the
closure is always computed: ``--with-deps`` bundles it, and without that flag
the tool prints exactly what else that customer must already have.

Upload the file anywhere reachable over HTTPS -- your own site, object storage,
a signed link -- and give the customer that URL. The deployment files take it
as MODULE_ARCHIVE_URL.
"""

import argparse
import ast
import hashlib
import pathlib
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
ADDONS = ROOT / "addons"

#: The catalogue's own version, used to name bundles. Individual modules are
#: named from their manifest version instead.
CATALOGUE_VERSION = "19.0.1.0.0"

# Never ship these.
EXCLUDE_DIRS = {"__pycache__", ".git", ".idea", ".vscode", "node_modules"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".pyd", ".log", ".swp"}
EXCLUDE_NAMES = {".DS_Store", "Thumbs.db"}

#: Modules that carry no licence gate of their own, and why. Everything else
#: must inherit hm.license.gate somewhere, or packaging refuses.
UNGATED = {
    "hm_license": "is the licence module",
    "af_jalali": "ships only widgets and services, with no documents to gate",
    "af_l10n_account": "ships only a chart-of-accounts template",
    "af_liaison": "gates through hm_expiry_docs, whose documents it extends",
}

#: Bundles sold as one thing. Dependencies are resolved on top of these, so a
#: suite lists what it is *about* rather than everything it drags in.
SUITES = {
    "hr": {
        "title": "HR and Payroll",
        "modules": ["hm_payroll", "af_hr_payroll", "af_hr", "hm_roster"],
    },
    "finance": {
        "title": "Finance",
        "modules": ["hm_account_reports", "hm_assets", "hm_contracts",
                    "af_l10n_account", "af_dual_currency", "af_zakat"],
    },
    "office": {
        "title": "Office Administration",
        "modules": ["hm_approvals", "hm_purchase_request", "af_procurement",
                    "af_correspondence", "hm_expiry_docs", "af_liaison",
                    "hm_frontdesk"],
    },
    "afghanistan": {
        "title": "Afghanistan Localization",
        "modules": ["af_jalali", "af_l10n_base", "af_l10n_account",
                    "af_dual_currency", "af_hr", "af_hr_payroll",
                    "af_procurement", "af_correspondence", "af_liaison",
                    "af_zakat"],
    },
    "complete": {
        "title": "Complete Catalogue",
        "modules": None,  # every module in addons/
    },
}


# ----------------------------------------------------------------------
# Reading the catalogue
# ----------------------------------------------------------------------

def all_modules():
    return sorted(p.name for p in ADDONS.iterdir()
                  if p.is_dir() and (p / "__manifest__.py").is_file())


def read_manifest(module):
    manifest_file = ADDONS / module / "__manifest__.py"
    if not manifest_file.is_file():
        raise SystemExit("No __manifest__.py in %s" % (ADDONS / module))
    text = manifest_file.read_text(encoding="utf-8")
    try:
        return ast.literal_eval(text[text.index("{"):text.rindex("}") + 1])
    except (ValueError, SyntaxError) as exc:
        raise SystemExit("Cannot parse %s: %s" % (manifest_file, exc))


def resolve_dependencies(modules):
    """Every module of ours that `modules` needs, including `modules`.

    Odoo's own modules are skipped: the customer already has those. Only the
    ones we would otherwise fail to deliver are returned.
    """
    ours = set(all_modules())
    seen = set()
    queue = list(modules)
    while queue:
        module = queue.pop()
        if module in seen:
            continue
        if module not in ours:
            raise SystemExit(
                "Module %r not found. Available: %s"
                % (module, ", ".join(sorted(ours)))
            )
        seen.add(module)
        queue.extend(d for d in read_manifest(module).get("depends", [])
                     if d in ours)
    return sorted(seen)


# ----------------------------------------------------------------------
# Guards
# ----------------------------------------------------------------------

def check_licence_key_is_real():
    """Refuse to ship a build whose gate is disarmed.

    hm_license only enforces once a genuine vendor public key has replaced the
    placeholder. Forgetting that step produces modules that install, run and
    never check anything -- a failure that is invisible precisely because
    everything works. So it is checked here, at the one point every customer
    copy has to pass through.
    """
    source = (ADDONS / "hm_license" / "models" / "hm_license.py").read_text(
        encoding="utf-8"
    )
    if "VENDOR_PUBLIC_KEY = PLACEHOLDER_PUBLIC_KEY" in source:
        raise SystemExit(
            """Refusing to package: hm_license still carries the placeholder
public key, so the licence gate would be inert in the customer's database.

    python tools/issue_license.py --generate-keys

Then put the public half into VENDOR_PUBLIC_KEY in
addons/hm_license/models/hm_license.py. Keep the private half off this
repository -- it is the only thing preventing anyone from minting licences."""
        )


def check_module_is_gated(module):
    """Refuse to ship a paid module that never asks whether it is licensed."""
    if module in UNGATED:
        return
    gated = any(
        "hm.license.gate" in p.read_text(encoding="utf-8")
        for p in (ADDONS / module).rglob("*.py")
        if "__pycache__" not in p.parts
    )
    if not gated:
        raise SystemExit(
            "Refusing to package %s: no model inherits hm.license.gate, so "
            "the module would never check its licence. Gate its main document "
            "model, or add it to UNGATED in this file with the reason." % module
        )


def check_licence_permits_sale(module):
    manifest = read_manifest(module)
    licence = manifest.get("license", "")
    if licence in ("AGPL-3", "GPL-3", "GPL-2"):
        raise SystemExit(
            "Refusing to package %s: its licence is %s, which obliges you to "
            "let customers redistribute it freely. See README.md."
            % (module, licence)
        )
    return licence


# ----------------------------------------------------------------------
# Building
# ----------------------------------------------------------------------

def should_include(path):
    if any(part in EXCLUDE_DIRS for part in path.parts):
        return False
    if path.suffix in EXCLUDE_SUFFIXES:
        return False
    return path.name not in EXCLUDE_NAMES


def files_for(module):
    root = ADDONS / module
    files = sorted(p for p in root.rglob("*") if p.is_file() and should_include(p))
    if not files:
        raise SystemExit("Nothing to package in %s" % root)
    return files


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_archive(archive, modules):
    check_licence_key_is_real()
    total = 0
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for module in modules:
            check_licence_permits_sale(module)
            check_module_is_gated(module)
            root = ADDONS / module
            for path in files_for(module):
                bundle.write(path, pathlib.Path(module) / path.relative_to(root))
                total += 1
    return total


def build_one(module, out_dir, with_deps=False):
    modules = resolve_dependencies([module]) if with_deps else [module]
    version = read_manifest(module).get("version", "0.0.0")
    suffix = "-with-dependencies" if with_deps and len(modules) > 1 else ""
    archive = out_dir / ("%s-%s%s.zip" % (module, version, suffix))
    count = write_archive(archive, modules)

    print("Packaged %s" % module)
    print("  version  : %s" % version)
    print("  licence  : %s" % read_manifest(module).get("license", ""))
    print("  contains : %s" % ", ".join(modules))
    print("  files    : %d" % count)
    print("  size     : %.1f KB" % (archive.stat().st_size / 1024))
    print("  archive  : %s" % archive)

    if not with_deps:
        needed = [m for m in resolve_dependencies([module]) if m != module]
        if needed:
            print()
            print("  NOTE: this archive contains %s alone. It will not install"
                  % module)
            print("  unless the customer already has: %s" % ", ".join(needed))
            print("  Use --with-deps to bundle them.")
    return archive, modules


def build_suite(name, out_dir):
    suite = SUITES[name]
    wanted = suite["modules"] or all_modules()
    modules = resolve_dependencies(wanted)
    archive = out_dir / ("hushmand-%s-%s.zip" % (name, CATALOGUE_VERSION))
    count = write_archive(archive, modules)

    print("Packaged the %s suite" % suite["title"])
    print("  modules : %d" % len(modules))
    print("  files   : %d" % count)
    print("  size    : %.1f KB" % (archive.stat().st_size / 1024))
    print("  archive : %s" % archive)
    extra = sorted(set(modules) - set(wanted))
    if extra:
        print("  pulled in as dependencies: %s" % ", ".join(extra))
    return archive, modules


def write_checksums(out_dir):
    """A customer receiving a link needs to know they got what was sent."""
    archives = sorted(out_dir.glob("*.zip"))
    if not archives:
        return None
    path = out_dir / "SHA256SUMS"
    path.write_text(
        "".join("%s  %s\n" % (sha256(a), a.name) for a in archives),
        encoding="utf-8",
    )
    return path


def plan(args):
    """Say what a delivery would contain, without producing one.

    Useful before quoting: it answers "what does this customer actually have
    to be licensed for?" -- which is the closure, not the one module they
    asked about. Writes nothing, so it needs no signing key.
    """
    if args.suite:
        suite = SUITES[args.suite]
        wanted = suite["modules"] or all_modules()
        modules = resolve_dependencies(wanted)
        print("Suite %s -- %s" % (args.suite, suite["title"]))
        print("  sold as    : %s" % ", ".join(sorted(wanted)))
        extra = sorted(set(modules) - set(wanted))
        print("  pulled in  : %s" % (", ".join(extra) if extra else "nothing"))
        print("  total      : %d modules" % len(modules))
        return 0

    targets = all_modules() if args.all else [args.module]
    for module in targets:
        needed = [m for m in resolve_dependencies([module]) if m != module]
        print("%-22s needs %s" % (
            module, ", ".join(needed) if needed else "nothing else of ours"))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module", nargs="?", help="module directory name")
    parser.add_argument("--all", action="store_true",
                        help="package every module separately")
    parser.add_argument("--suite", choices=sorted(SUITES),
                        help="package a bundle sold as one thing")
    parser.add_argument("--with-deps", action="store_true",
                        help="include the other modules of ours it needs")
    parser.add_argument("--out", default=str(ROOT / "dist"),
                        help="output directory")
    parser.add_argument("--plan", action="store_true",
                        help="show what would be packaged, and write nothing")
    args = parser.parse_args()

    if sum(bool(x) for x in (args.module, args.all, args.suite)) != 1:
        parser.error("give exactly one of: a module name, --all, or --suite")

    if args.plan:
        return plan(args)

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.suite:
        build_suite(args.suite, out_dir)
    elif args.all:
        for module in all_modules():
            build_one(module, out_dir, with_deps=args.with_deps)
            print()
    else:
        build_one(args.module, out_dir, with_deps=args.with_deps)

    checksums = write_checksums(out_dir)
    if checksums:
        print()
        print("Checksums for everything in %s: %s" % (out_dir, checksums.name))
    print()
    print("Upload the archive over HTTPS and give the customer the link as")
    print("MODULE_ARCHIVE_URL in the deployment file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
