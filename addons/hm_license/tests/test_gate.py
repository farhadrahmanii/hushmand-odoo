# Part of hm_license. See LICENSE file for full copyright and licensing details.
"""Tests for the gate: the part that costs an unlicensed user something.

Verifying a signature is only half a licence system. The half that decides
whether the product earns money is what happens on a customer's machine when
the signature is missing, and the half that decides whether they renew is what
happens the morning after it lapses.
"""

import ast
import pathlib

from odoo.addons.hm_license.models.hm_license import GRACE_DAYS
from odoo.addons.hm_license.tests.common import LicenceKeyMixin
from odoo.exceptions import UserError
from odoo.tests import common, new_test_user, tagged

ADDONS = pathlib.Path(__file__).resolve().parents[2]
ROOT = ADDONS.parent


@tagged("post_install", "-at_install")
class GateCase(LicenceKeyMixin, common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.setUpLicenceKeys()
        cls.Licence = cls.env["hm.license"]
        # The mixin itself is the smallest thing carrying the gate, and unlike
        # any concrete model it is present wherever hm_license is.
        cls.gate = cls.env["hm.license.gate"]

    def setUp(self):
        super().setUp()
        self.Licence.search([]).unlink()


class TestArming(GateCase):

    def test_a_development_checkout_enforces_nothing(self):
        """The placeholder key means there is no vendor to enforce for.

        That is what keeps every other module in the catalogue testable
        without a signed licence, so it is worth stating as a test rather
        than leaving as an accident of the code.
        """
        self.assertFalse(self.Licence.enforced())

    def test_a_real_key_arms_the_gate(self):
        with self.armed():
            self.assertTrue(self.Licence.enforced())

    def test_an_unarmed_gate_lets_everything_through(self):
        """No licence, no key, no complaint."""
        self.gate._licence_gate_check()


class TestTheGateRefuses(GateCase):

    def test_no_licence_stops_new_work(self):
        with self.armed():
            with self.assertRaises(UserError) as caught:
                self.gate._licence_gate_check()
        self.assertIn("No licence", str(caught.exception))

    def test_the_refusal_says_how_to_fix_it(self):
        """A block with no next step produces a support ticket, not a sale."""
        with self.armed():
            with self.assertRaises(UserError) as caught:
                self.gate._licence_gate_check()
        self.assertIn("supplier", str(caught.exception).lower())

    def test_a_licence_for_other_modules_does_not_cover_this_one(self):
        with self.armed():
            self.install_licence(["hm_payroll"])
            with self.assertRaises(UserError) as caught:
                self.gate._licence_gate_check()
        self.assertIn("hm_license", str(caught.exception))

    def test_a_covering_licence_lets_work_through(self):
        with self.armed():
            self.install_licence(["hm_license"])
            self.gate._licence_gate_check()

    def test_the_module_checked_defaults_to_the_declaring_one(self):
        """A model that forgets to set _licence_module still checks its own
        module rather than silently checking nothing."""
        self.assertEqual(self.gate._original_module, "hm_license")


class TestTheGraceMonth(GateCase):

    def test_a_licence_lapsed_yesterday_still_works(self):
        """Payroll must not stop on the morning a renewal invoice is late."""
        with self.armed():
            licence = self.install_licence(["hm_license"], days=-1)
            self.assertEqual(licence.state, "grace")
            self.gate._licence_gate_check()

    def test_the_grace_state_counts_down_in_words(self):
        with self.armed():
            licence = self.install_licence(["hm_license"], days=-1)
        self.assertIn("stops accepting new work", licence.status_detail)

    def test_the_last_day_of_grace_still_works(self):
        with self.armed():
            self.install_licence(["hm_license"], days=-GRACE_DAYS)
            self.gate._licence_gate_check()

    def test_past_the_grace_month_the_gate_closes(self):
        with self.armed():
            licence = self.install_licence(["hm_license"], days=-GRACE_DAYS - 1)
            self.assertEqual(licence.state, "expired")
            with self.assertRaises(UserError):
                self.gate._licence_gate_check()

    def test_the_expired_message_names_the_grace_period(self):
        with self.armed():
            self.install_licence(["hm_license"], days=-GRACE_DAYS - 1)
            ok, message = self.Licence.check()
        self.assertFalse(ok)
        self.assertIn(str(GRACE_DAYS), message)


class TestTheIndicator(GateCase):

    def test_an_unarmed_build_shows_nothing(self):
        self.assertEqual(self.Licence.status()["level"], "off")

    def test_a_missing_licence_is_a_danger(self):
        with self.armed():
            status = self.Licence.status()
        self.assertEqual(status["level"], "danger")
        self.assertEqual(status["state"], "missing")

    def test_a_healthy_licence_shows_nothing(self):
        """An indicator that is always lit is one nobody reads."""
        with self.armed():
            self.install_licence(["hm_license"])
            status = self.Licence.status()
        self.assertEqual(status["level"], "ok")
        self.assertFalse(status["message"])

    def test_an_expiring_licence_warns(self):
        with self.armed():
            self.install_licence(["hm_license"], days=10)
            status = self.Licence.status()
        self.assertEqual(status["level"], "warning")
        self.assertEqual(status["state"], "expiring")

    def test_a_lapsed_licence_warns_with_the_deadline(self):
        with self.armed():
            self.install_licence(["hm_license"], days=-2)
            status = self.Licence.status()
        self.assertEqual(status["state"], "grace")
        self.assertIn("day(s)", status["message"])

    def test_an_expired_licence_is_a_danger(self):
        with self.armed():
            self.install_licence(["hm_license"], days=-GRACE_DAYS - 1)
            status = self.Licence.status()
        self.assertEqual(status["level"], "danger")
        self.assertEqual(status["state"], "expired")

    def test_too_many_users_warns_without_blocking(self):
        with self.armed():
            self.install_licence(["hm_license"], max_users=1)
            new_test_user(self.env, login="gate_seat_a")
            new_test_user(self.env, login="gate_seat_b")
            self.Licence.invalidate_model()
            status = self.Licence.status()
        self.assertEqual(status["state"], "over_users")
        self.assertEqual(status["level"], "warning")

    def test_the_indicator_never_returns_the_key(self):
        """Every internal user reads this, not only the administrator."""
        with self.armed():
            self.install_licence(["hm_license"])
            status = self.Licence.status()
        self.assertEqual(set(status), {"level", "message", "state"})


@tagged("post_install", "-at_install")
class TestTheCatalogueIsGated(common.TransactionCase):
    """A module added later must not quietly ship without a gate.

    This is the check that stops the feature from rotting. A missing gate is
    invisible -- the module installs, runs and sells exactly as it should --
    so nothing else would ever notice.
    """

    @classmethod
    def _ungated(cls):
        """The exemptions declared in tools/build_release.py.

        Read from there rather than repeated here, so the packaging guard and
        this test cannot drift apart and disagree about what is exempt.
        """
        source = (ROOT / "tools" / "build_release.py").read_text(encoding="utf-8")
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Assign) and any(
                getattr(target, "id", None) == "UNGATED" for target in node.targets
            ):
                return set(ast.literal_eval(node.value))
        raise AssertionError("tools/build_release.py no longer declares UNGATED")

    def _modules(self):
        return sorted(p.name for p in ADDONS.iterdir() if p.is_dir())

    def test_every_paid_module_carries_the_gate(self):
        ungated = self._ungated()
        missing = []
        for module in self._modules():
            if module in ungated:
                continue
            gated = any(
                "hm.license.gate" in path.read_text(encoding="utf-8")
                for path in (ADDONS / module).rglob("*.py")
                if "__pycache__" not in path.parts
            )
            if not gated:
                missing.append(module)
        self.assertFalse(
            missing,
            "these modules never check their licence: %s. Gate the main "
            "document model, or declare the exemption in UNGATED in "
            "tools/build_release.py." % ", ".join(missing),
        )

    def test_every_module_depends_on_hm_license(self):
        missing = []
        for module in self._modules():
            if module == "hm_license":
                continue
            manifest = (ADDONS / module / "__manifest__.py").read_text(
                encoding="utf-8"
            )
            depends = ast.literal_eval(
                manifest[manifest.index("{"):manifest.rindex("}") + 1]
            ).get("depends", [])
            if "hm_license" not in depends:
                missing.append(module)
        self.assertFalse(
            missing,
            "these modules can be installed without the licence app: %s"
            % ", ".join(missing),
        )

    def test_the_exemptions_are_all_real_modules(self):
        """A typo in UNGATED exempts nothing and hides a real gap."""
        for module in self._ungated():
            self.assertTrue(
                (ADDONS / module).is_dir(),
                "UNGATED names %s, which is not a module" % module,
            )
