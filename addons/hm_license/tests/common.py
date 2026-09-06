# Part of hm_license. See LICENSE file for full copyright and licensing details.
"""Minting signed licences inside a test.

Every module in the catalogue now refuses to accept new work without a
licence, so every module's tests need a way to hand themselves one. They do it
the way a customer's database does: a real Ed25519 signature, verified by the
real code path. Nothing here is mocked, because a mocked signature check would
pass just as happily over a broken one.

The keypair is generated per test run and thrown away. No private key is
committed anywhere -- that is the entire premise of the design.

    class TestSomething(LicenceKeyMixin, common.TransactionCase):

        @classmethod
        def setUpClass(cls):
            super().setUpClass()
            cls.setUpLicenceKeys()

        def test_it(self):
            with self.armed():
                self.install_licence(["hm_payroll"])
                ...
"""

import base64
import json
from datetime import date, timedelta
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

#: Where VENDOR_PUBLIC_KEY lives, for patching.
LICENCE_MODULE = "odoo.addons.hm_license.models.hm_license"


class LicenceKeyMixin:
    """Sign licences with a throwaway keypair."""

    @classmethod
    def setUpLicenceKeys(cls):
        cls.signing_key = Ed25519PrivateKey.generate()
        cls.public_b64 = base64.b64encode(
            cls.signing_key.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        ).decode()
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
        payload = payload if payload is not None else self._payload()
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

    def _with_key(self):
        """Patch this run's public key into the module under test.

        Doubles as the switch that arms the gate: hm_license only enforces
        once a real vendor key has replaced the placeholder.
        """
        return patch.object(
            __import__(LICENCE_MODULE, fromlist=["x"]),
            "VENDOR_PUBLIC_KEY",
            self.public_b64,
        )

    #: Reads better at the call site of a gate test than ``_with_key``.
    armed = _with_key

    def unarmed(self):
        """Put the placeholder key back, whatever this checkout carries.

        A test about how an unconfigured build behaves must say so, rather
        than relying on the repository not yet having a vendor key. That
        assumption held until the day it stopped holding, and then six tests
        failed at once for a reason that had nothing to do with them.
        """
        module = __import__(LICENCE_MODULE, fromlist=["x"])
        return patch.object(
            module, "VENDOR_PUBLIC_KEY", module.PLACEHOLDER_PUBLIC_KEY
        )

    def _install(self, payload=None, signer=None):
        with self._with_key():
            return self.env["hm.license"].create({"key": self._key(payload, signer)})

    def install_licence(self, modules, days=365, **overrides):
        """Enter a licence covering ``modules``. Assumes the gate is armed."""
        return self.env["hm.license"].create({
            "key": self._key(self._payload(
                modules=modules,
                expires=(self.today + timedelta(days=days)).isoformat(),
                **overrides,
            )),
        })
