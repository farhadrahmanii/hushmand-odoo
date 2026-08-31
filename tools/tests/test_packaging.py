# Part of the Hushmand Odoo addons tooling.
"""Tests for the release packaging.

Tier 0: no Odoo, no database. These run in the fast CI job.

What is being protected here is a delivery, and a delivery fails at the
customer's site on the day they try to install it. Everything below is a thing
that would look fine in dist/ and go wrong there.
"""

import pathlib
import sys
import unittest
import zipfile
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import build_release  # noqa: E402


class TestDependencyClosure(unittest.TestCase):
    """The archive has to contain everything Odoo will ask for."""

    def test_a_module_is_in_its_own_closure(self):
        self.assertIn("af_jalali", build_release.resolve_dependencies(["af_jalali"]))

    def test_the_closure_is_transitive(self):
        """af_procurement -> hm_purchase_request -> hm_approvals.

        The middle module is the one a hand-written list forgets.
        """
        closure = build_release.resolve_dependencies(["af_procurement"])
        self.assertIn("hm_purchase_request", closure)
        self.assertIn("hm_approvals", closure)

    def test_every_module_needs_the_licence_module(self):
        """Every paid module depends on hm_license, so every delivery must
        carry it. A bundle without it installs nothing at all."""
        for module in build_release.all_modules():
            if module == "hm_license":
                continue
            with self.subTest(module=module):
                self.assertIn(
                    "hm_license", build_release.resolve_dependencies([module])
                )

    def test_odoo_s_own_modules_are_not_in_the_closure(self):
        """The customer already has account, hr and purchase. Shipping them
        would be both pointless and a licence violation."""
        closure = build_release.resolve_dependencies(["hm_payroll"])
        for core in ("hr", "account", "mail", "base", "purchase"):
            self.assertNotIn(core, closure)

    def test_an_unknown_module_is_refused_by_name(self):
        with self.assertRaises(SystemExit) as caught:
            build_release.resolve_dependencies(["af_mining"])
        self.assertIn("af_mining", str(caught.exception))

    def test_the_closure_terminates_on_the_real_catalogue(self):
        """A cycle in depends would hang the packager rather than fail it."""
        for module in build_release.all_modules():
            with self.subTest(module=module):
                self.assertTrue(build_release.resolve_dependencies([module]))


class TestSuites(unittest.TestCase):

    def test_every_suite_names_real_modules(self):
        catalogue = set(build_release.all_modules())
        for name, suite in build_release.SUITES.items():
            if suite["modules"] is None:
                continue
            with self.subTest(suite=name):
                unknown = set(suite["modules"]) - catalogue
                self.assertFalse(unknown, "suite %s names %s" % (name, unknown))

    def test_every_suite_resolves_to_an_installable_set(self):
        """Resolving a suite twice must not grow it. If it does, something in
        the closure was missed and the bundle is short a module."""
        for name in build_release.SUITES:
            with self.subTest(suite=name):
                wanted = (build_release.SUITES[name]["modules"]
                          or build_release.all_modules())
                once = build_release.resolve_dependencies(wanted)
                twice = build_release.resolve_dependencies(once)
                self.assertEqual(once, twice)

    def test_the_complete_suite_is_the_whole_catalogue(self):
        modules = build_release.resolve_dependencies(build_release.all_modules())
        self.assertEqual(sorted(modules), build_release.all_modules())


class TestTheKeyGuard(unittest.TestCase):

    def test_packaging_is_refused_while_the_key_is_a_placeholder(self):
        """The whole point of the guard: a build with the gate disarmed
        installs, runs, sells, and checks nothing."""
        source = (ROOT / "addons" / "hm_license" / "models"
                  / "hm_license.py").read_text(encoding="utf-8")
        placeholder = "VENDOR_PUBLIC_KEY = PLACEHOLDER_PUBLIC_KEY" in source
        if not placeholder:
            self.skipTest("a real vendor key is configured in this checkout")
        with self.assertRaises(SystemExit) as caught:
            build_release.check_licence_key_is_real()
        self.assertIn("issue_license.py", str(caught.exception))


class TestWhatEndsUpInTheArchive(unittest.TestCase):
    """Archive layout, with the key guard stood down.

    The guard is tested above. Here it is patched out so the packaging itself
    can be checked on a checkout that has no signing key -- which is every
    checkout in CI.
    """

    def build(self, modules, name="test.zip"):
        import tempfile
        out = pathlib.Path(tempfile.mkdtemp()) / name
        with patch.object(build_release, "check_licence_key_is_real"):
            build_release.write_archive(out, modules)
        return out

    def test_the_archive_unpacks_to_one_folder_per_module(self):
        archive = self.build(["af_jalali", "hm_license"])
        with zipfile.ZipFile(archive) as bundle:
            roots = {name.split("/")[0] for name in bundle.namelist()}
        self.assertEqual(roots, {"af_jalali", "hm_license"})

    def test_the_manifest_is_at_the_top_of_its_folder(self):
        """Odoo finds a module by addons_path/<name>/__manifest__.py. One
        level of nesting wrong and the module is invisible."""
        archive = self.build(["af_jalali"])
        with zipfile.ZipFile(archive) as bundle:
            self.assertIn("af_jalali/__manifest__.py", bundle.namelist())

    def test_compiled_python_is_never_shipped(self):
        """A .pyc from the developer's machine can shadow the .py it was
        built from and run stale code on the customer's."""
        archive = self.build(build_release.all_modules())
        with zipfile.ZipFile(archive) as bundle:
            names = bundle.namelist()
        self.assertFalse([n for n in names if n.endswith(".pyc")])
        self.assertFalse([n for n in names if "__pycache__" in n])

    def test_the_licence_text_ships_with_every_module(self):
        archive = self.build(["hm_payroll"])
        with zipfile.ZipFile(archive) as bundle:
            names = bundle.namelist()
        self.assertIn("hm_payroll/README.md", names)
        self.assertIn("hm_payroll/static/description/index.html", names)

    def test_an_agpl_module_would_be_refused(self):
        """Nothing in the catalogue is AGPL, so the guard is exercised with a
        forged manifest rather than left unproven."""
        forged = dict(build_release.read_manifest("af_jalali"), license="AGPL-3")
        with patch.object(build_release, "read_manifest", return_value=forged):
            with self.assertRaises(SystemExit) as caught:
                build_release.check_licence_permits_sale("af_jalali")
        self.assertIn("AGPL-3", str(caught.exception))


class TestChecksums(unittest.TestCase):

    def test_a_checksum_file_lists_every_archive(self):
        import tempfile
        out = pathlib.Path(tempfile.mkdtemp())
        with patch.object(build_release, "check_licence_key_is_real"):
            build_release.write_archive(out / "one.zip", ["af_jalali"])
            build_release.write_archive(out / "two.zip", ["hm_license"])
        listing = build_release.write_checksums(out).read_text(encoding="utf-8")
        self.assertIn("one.zip", listing)
        self.assertIn("two.zip", listing)
        for line in listing.strip().split("\n"):
            self.assertEqual(len(line.split("  ")[0]), 64)


if __name__ == "__main__":
    unittest.main()
