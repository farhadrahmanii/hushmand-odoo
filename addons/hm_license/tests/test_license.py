# Part of hm_license. See LICENSE file for full copyright and licensing details.
"""Tests for licence verification.

These sign real licences with a throwaway keypair generated in the test, so
the actual cryptography is exercised rather than mocked. No private key is
committed anywhere: the point of the design is that only the vendor holds one.
"""

import base64
import json
from datetime import date, timedelta
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from odoo.exceptions import UserError, ValidationError
from odoo.tests import common, tagged
from odoo.tools import mute_logger

MODULE = "odoo.addons.hm_license.models.hm_license"


@tagged("post_install", "-at_install")
class LicenceCase(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.signing_key = Ed25519PrivateKey.generate()
        cls.public_b64 = base64.b64encode(
            cls.signing_key.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        ).decode()
        cls.Licence = cls.env["hm.license"]
        cls.today = date.today()

    def _payload(self, **overrides):
        payload = {
            "licence_id": "TEST-0001",
            "customer": "Test Customer",
            "modules": ["af_jalali", "af_hr"],
            "features": [],
            "issued": self.today.isoformat(),
            "expires": (self.today + timedelta(days=365)).isoformat(),
            "max_users": 0,
        }
        payload.update(overrides)
        return payload

    def _key(self, payload=None, signer=None):
        """Produce a licence key the way the issuing tool does."""
        payload = payload or self._payload()
        signer = signer or self.signing_key
        payload_bytes = json.dumps(
            payload, sort_keys=True, separators=(",", ":")
        ).encode()
        envelope = {
            "payload": payload,
            "sig": base64.b64encode(signer.sign(payload_bytes)).decode(),
        }
        return base64.b64encode(
            json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
        ).decode()

    def _install(self, payload=None, signer=None):
        with patch.object(
            __import__(MODULE, fromlist=["x"]), "VENDOR_PUBLIC_KEY",
            self.public_b64,
        ):
            return self.Licence.create({"key": self._key(payload, signer)})

    def _with_key(self):
        """Context manager patching in this test's public key."""
        return patch.object(
            __import__(MODULE, fromlist=["x"]), "VENDOR_PUBLIC_KEY",
            self.public_b64,
        )


class TestVerification(LicenceCase):

    def test_a_properly_signed_licence_is_accepted(self):
        licence = self._install()
        self.assertEqual(licence.state, "valid")
        self.assertEqual(licence.customer, "Test Customer")
        self.assertEqual(licence.licence_id, "TEST-0001")

    def test_the_payload_is_read_out_of_the_key(self):
        licence = self._install()
        self.assertIn("af_jalali", licence.modules)
        self.assertIn("af_hr", licence.modules)

    @mute_logger(MODULE)
    def test_a_licence_signed_by_someone_else_is_rejected(self):
        """The whole point: a key minted with a different private key must
        not verify."""
        impostor = Ed25519PrivateKey.generate()
        licence = self._install(signer=impostor)
        self.assertEqual(licence.state, "invalid")
        self.assertIn("signature", licence.status_detail.lower())

    @mute_logger(MODULE)
    def test_an_edited_payload_is_rejected(self):
        """Raising max_users by hand must invalidate the signature."""
        payload = self._payload(max_users=5)
        key = self._key(payload)

        envelope = json.loads(base64.b64decode(key))
        envelope["payload"]["max_users"] = 5000
        tampered = base64.b64encode(
            json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
        ).decode()

        with self._with_key():
            licence = self.Licence.create({"key": tampered})
        self.assertEqual(licence.state, "invalid")

    def test_an_unconfigured_build_says_so(self):
        """A fresh checkout has no signing key. It should say that, not
        report a mystifying signature mismatch."""
        with self.assertRaises(UserError) as caught:
            self.Licence.create({"key": self._key()})
        self.assertIn("signing key", str(caught.exception).lower())

    def test_gibberish_is_refused_clearly(self):
        with self.assertRaises(ValidationError):
            self.Licence.create({"key": "not a licence at all"})

    def test_an_empty_key_is_refused(self):
        with self.assertRaises(ValidationError):
            self.Licence.create({"key": "   "})

    def test_whitespace_in_a_pasted_key_is_tolerated(self):
        """Keys are printed in wrapped lines and arrive out of an email."""
        key = self._key()
        wrapped = "\n".join(key[i:i + 40] for i in range(0, len(key), 40))
        with self._with_key():
            licence = self.Licence.create({"key": wrapped})
        self.assertEqual(licence.state, "valid")

    @mute_logger(MODULE)
    def test_a_licence_missing_claims_is_rejected(self):
        payload = self._payload()
        del payload["customer"]
        licence = self._install(payload=payload)
        self.assertEqual(licence.state, "invalid")


class TestExpiry(LicenceCase):

    def test_valid_well_before_expiry(self):
        self.assertEqual(self._install().state, "valid")

    def test_expiring_inside_thirty_days(self):
        licence = self._install(self._payload(
            expires=(self.today + timedelta(days=10)).isoformat()
        ))
        self.assertEqual(licence.state, "expiring")

    def test_expired_once_past(self):
        licence = self._install(self._payload(
            licence_id="TEST-OLD",
            expires=(self.today - timedelta(days=1)).isoformat(),
        ))
        self.assertEqual(licence.state, "expired")

    def test_the_status_says_why(self):
        licence = self._install()
        self.assertTrue(licence.status_detail)


class TestTheGate(LicenceCase):

    def test_no_licence_means_not_licensed(self):
        self.Licence.search([]).unlink()
        ok, message = self.Licence.check()
        self.assertFalse(ok)
        self.assertIn("No licence", message)

    def test_a_valid_licence_passes(self):
        self.Licence.search([]).unlink()
        self._install()
        ok, _message = self.Licence.check()
        self.assertTrue(ok)

    def test_an_expired_licence_fails(self):
        self.Licence.search([]).unlink()
        self._install(self._payload(
            expires=(self.today - timedelta(days=1)).isoformat()
        ))
        ok, message = self.Licence.check()
        self.assertFalse(ok)
        self.assertIn("expired", message.lower())

    def test_a_module_outside_the_licence_fails(self):
        self.Licence.search([]).unlink()
        self._install()
        ok, message = self.Licence.check("hm_payroll")
        self.assertFalse(ok)
        self.assertIn("hm_payroll", message)

    def test_a_module_inside_the_licence_passes(self):
        self.Licence.search([]).unlink()
        self._install()
        ok, _message = self.Licence.check("af_jalali")
        self.assertTrue(ok)

    def test_require_raises_when_unlicensed(self):
        self.Licence.search([]).unlink()
        with self.assertRaises(UserError):
            self.Licence.require()

    def test_require_passes_when_licensed(self):
        self.Licence.search([]).unlink()
        self._install()
        self.assertTrue(self.Licence.require("af_hr"))


class TestUserLimit(LicenceCase):

    def test_unlimited_when_zero(self):
        licence = self._install()
        self.assertEqual(licence.max_users, 0)
        self.assertFalse(licence.over_user_limit)

    def test_over_the_limit_is_detected(self):
        licence = self._install(self._payload(max_users=1))
        licence.invalidate_recordset(["active_users", "over_user_limit"])
        self.assertTrue(
            licence.over_user_limit,
            "a demo database has more than one internal user",
        )

    def test_the_gate_refuses_over_the_limit(self):
        self.Licence.search([]).unlink()
        self._install(self._payload(max_users=1))
        ok, message = self.Licence.check()
        self.assertFalse(ok)
        self.assertIn("are active", message)


class TestHousekeeping(LicenceCase):

    @mute_logger("odoo.sql_db")
    def test_the_same_licence_cannot_be_entered_twice(self):
        self.Licence.search([]).unlink()
        self._install()
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self._install()

    def test_replacing_the_key_reverifies(self):
        licence = self._install()
        self.assertEqual(licence.state, "valid")

        renewed = self._payload(
            licence_id="TEST-0001",
            expires=(self.today + timedelta(days=800)).isoformat(),
        )
        with self._with_key():
            licence.key = self._key(renewed)

        self.assertEqual(licence.expires, self.today + timedelta(days=800))

    def test_cron_refreshes_status(self):
        self.Licence.search([]).unlink()
        licence = self._install()
        # Flush first: the create's own write is still pending, and would
        # otherwise be written *after* this raw UPDATE and undo it.
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE hm_license SET expires = %s, state = 'valid' WHERE id = %s",
            (self.today - timedelta(days=5), licence.id),
        )
        self.env.invalidate_all()
        self.assertEqual(licence.state, "valid", "precondition: stale status")

        self.Licence._cron_refresh()
        self.assertEqual(licence.state, "expired")
