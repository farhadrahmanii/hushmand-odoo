#!/usr/bin/env python
"""Run the Tier 0 tests without an Odoo installation.

The conversion core imports nothing from Odoo, so it can be tested in a plain
Python interpreter. That keeps the feedback loop fast and proves the core is
genuinely version-independent.

    python tools/run_core_tests.py

The Tier 1 tests (models, QWeb widgets) need a running Odoo and are executed by
the Odoo test runner instead:

    odoo -d <db> -i af_jalali --test-enable --stop-after-init
"""

import importlib
import pathlib
import sys
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Modules to run. Anything importing odoo belongs in the Odoo runner, not here.
CORE_TEST_MODULES = [
    "test_jalali_core",
    "test_jalali_formats",
]


def _stub_package(name, path):
    """Register a namespace package without executing its __init__.

    ``af_jalali/__init__.py`` imports the models, which import Odoo. Stubbing
    the package lets the relative imports inside the tests resolve while
    skipping that chain.
    """
    module = types.ModuleType(name)
    module.__path__ = [str(path)]
    sys.modules[name] = module
    return module


def build_suite(addon="af_jalali"):
    addon_path = ROOT / "addons" / addon
    if not addon_path.is_dir():
        raise SystemExit("Addon not found: %s" % addon_path)

    _stub_package(addon, addon_path)
    _stub_package("%s.tests" % addon, addon_path / "tests")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for name in CORE_TEST_MODULES:
        module = importlib.import_module("%s.tests.%s" % (addon, name))
        suite.addTests(loader.loadTestsFromModule(module))
    return suite


def main():
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(build_suite())
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
