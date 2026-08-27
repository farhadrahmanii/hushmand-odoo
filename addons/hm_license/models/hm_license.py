# Part of hm_license. See LICENSE file for full copyright and licensing details.
"""Licence keys.

A licence is a small JSON document -- who it is for, what it covers, when it
expires, how many users -- signed with an Ed25519 private key the vendor
holds. The public key is embedded below. Verification is therefore entirely
offline: no server to call, nothing to break when a customer's internet does,
and no telemetry leaving their database.

What this is not
----------------

It is not DRM. Odoo modules ship as readable Python, so anybody sufficiently
determined can edit this file. That is equally true of every paid module on
the Odoo App Store.

The purpose is to make the licence *legible*: the customer can see what they
bought, when it lapses, and whether they have outgrown it, and the vendor has
something concrete to point at. Enforcement is contractual. This is the part
that keeps honest customers honest and makes renewals a conversation rather
than an accusation.
"""

import base64
import json
import logging
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PublicKey,
    )
except ImportError:  # pragma: no cover - cryptography ships with Odoo
    Ed25519PublicKey = None
    InvalidSignature = Exception

#: Sentinel meaning "no key has been set yet". Checked explicitly so a fresh
#: checkout fails with an instruction rather than a silent signature mismatch.
PLACEHOLDER_PUBLIC_KEY = "REPLACE-WITH-YOUR-OWN-PUBLIC-KEY"

#: The vendor's public key, base64 of 32 raw bytes. Safe to publish -- that is
#: what makes it a public key.
#:
#: Generate your own before issuing anything:
#:
#:     python tools/issue_license.py --generate-keys
#:
#: The private half must never reach this repository or a customer. It is the
#: only thing preventing anyone from minting their own licences.
VENDOR_PUBLIC_KEY = PLACEHOLDER_PUBLIC_KEY

#: Payload fields a licence must carry to be considered well-formed.
REQUIRED_CLAIMS = ("licence_id", "customer", "modules", "expires")


class HmLicense(models.Model):
    _name = "hm.license"
    _description = "Licence"
    _inherit = ["mail.thread"]
    _order = "id desc"

    name = fields.Char(
        string="Licence", compute="_compute_name", store=True,
    )
    key = fields.Text(
        string="Licence Key",
        required=True,
        copy=False,
        help="The block of text supplied with your purchase. Paste it whole.",
    )

    # Everything below is read out of the signed payload. None of it is
    # editable: a licence you can retype is not a licence.
    licence_id = fields.Char(readonly=True)
    customer = fields.Char(readonly=True)
    modules = fields.Char(
        string="Covers", readonly=True,
        help="Modules this licence entitles you to use.",
    )
    issued = fields.Date(readonly=True)
    expires = fields.Date(readonly=True, tracking=True)
    max_users = fields.Integer(
        readonly=True,
        help="Zero means no limit.",
    )
    features = fields.Char(readonly=True)

    state = fields.Selection(
        selection=[
            ("invalid", "Not Valid"),
            ("valid", "Valid"),
            ("expiring", "Expiring Soon"),
            ("expired", "Expired"),
        ],
        default="invalid",
        readonly=True,
        tracking=True,
        index=True,
    )
    status_detail = fields.Char(
        string="Detail", readonly=True,
        help="Why the licence is in this state, in plain words.",
    )
    active_users = fields.Integer(
        string="Users In Use", compute="_compute_active_users",
    )
    over_user_limit = fields.Boolean(compute="_compute_active_users")
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )

    _licence_unique = models.Constraint(
        "unique(licence_id)",
        "That licence has already been entered.",
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------

    @api.depends("customer", "licence_id")
    def _compute_name(self):
        for licence in self:
            licence.name = licence.customer or licence.licence_id or _("Licence")

    def _compute_active_users(self):
        internal = self.env["res.users"].search_count([
            ("active", "=", True),
            ("share", "=", False),
        ])
        for licence in self:
            licence.active_users = internal
            licence.over_user_limit = bool(
                licence.max_users and internal > licence.max_users
            )

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    @api.model
    def _decode(self, key):
        """Split a pasted key into its payload and signature.

        The wire format is base64 of ``{"payload": {...}, "sig": "..."}``,
        wrapped so it survives being pasted out of an email.
        """
        cleaned = "".join((key or "").split())
        if not cleaned:
            raise ValidationError(_("The licence key is empty."))
        try:
            raw = base64.b64decode(cleaned, validate=True)
            envelope = json.loads(raw.decode("utf-8"))
            payload = envelope["payload"]
            signature = base64.b64decode(envelope["sig"])
            payload_bytes = json.dumps(
                payload, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        except (ValueError, KeyError, TypeError) as exc:
            raise ValidationError(
                _("That does not look like a licence key. Paste the whole "
                  "block exactly as it was supplied.")
            ) from exc
        return payload, payload_bytes, signature

    @api.model
    def _verify_signature(self, payload_bytes, signature):
        if Ed25519PublicKey is None:
            raise UserError(
                _("This installation cannot verify licences: the cryptography "
                  "library is missing.")
            )
        if VENDOR_PUBLIC_KEY == PLACEHOLDER_PUBLIC_KEY:
            # Failing here with an instruction beats a mystifying signature
            # mismatch on a build nobody has configured yet.
            raise UserError(
                _("No signing key has been configured for this build. Run "
                  "tools/issue_license.py --generate-keys and put the public "
                  "key into hm_license.")
            )
        try:
            public_key = Ed25519PublicKey.from_public_bytes(
                base64.b64decode(VENDOR_PUBLIC_KEY)
            )
            public_key.verify(signature, payload_bytes)
        except (InvalidSignature, ValueError):
            return False
        return True

    def action_verify(self):
        """Read the key, check the signature, and record what it says."""
        for licence in self:
            payload, payload_bytes, signature = self._decode(licence.key)

            if not self._verify_signature(payload_bytes, signature):
                licence._mark_invalid(
                    _("The signature does not match. This key has been "
                      "altered, or was not issued for this product.")
                )
                continue

            missing = [c for c in REQUIRED_CLAIMS if not payload.get(c)]
            if missing:
                licence._mark_invalid(
                    _("The licence is missing: %s") % ", ".join(missing)
                )
                continue

            licence._apply_payload(payload)
        return True

    def _apply_payload(self, payload):
        self.ensure_one()
        modules = payload.get("modules") or []
        features = payload.get("features") or []
        self.write({
            "licence_id": payload["licence_id"],
            "customer": payload["customer"],
            "modules": ", ".join(modules) if isinstance(modules, list) else modules,
            "features": ", ".join(features) if isinstance(features, list) else features,
            "issued": payload.get("issued") or False,
            "expires": payload["expires"],
            "max_users": payload.get("max_users") or 0,
        })
        self._refresh_state()

    def _mark_invalid(self, reason):
        self.ensure_one()
        self.write({"state": "invalid", "status_detail": reason})
        _logger.warning("Licence rejected: %s", reason)

    def _refresh_state(self):
        """Set the state from the expiry date.

        Not a computed field, for the same reason as everywhere else in this
        catalogue: it depends on today, and a stored compute does not re-run
        as the calendar moves.
        """
        today = fields.Date.context_today(self)
        for licence in self:
            if not licence.licence_id or not licence.expires:
                continue
            days_left = (licence.expires - today).days
            if days_left < 0:
                licence.write({
                    "state": "expired",
                    "status_detail": _("Expired on %s.") % licence.expires,
                })
            elif days_left <= 30:
                licence.write({
                    "state": "expiring",
                    "status_detail": _("Expires in %s day(s).") % days_left,
                })
            else:
                licence.write({
                    "state": "valid",
                    "status_detail": _("Valid until %s.") % licence.expires,
                })

    @api.model_create_multi
    def create(self, vals_list):
        licences = super().create(vals_list)
        licences.action_verify()
        return licences

    def write(self, vals):
        result = super().write(vals)
        if "key" in vals:
            self.action_verify()
        return result

    # ------------------------------------------------------------------
    # The gate other modules use
    # ------------------------------------------------------------------

    @api.model
    def check(self, module=None):
        """Whether the installation is licensed, and why not if it is not.

        :return: ``(ok, message)``. ``ok`` is False for an absent, invalid or
            expired licence, or one that does not cover ``module``.
        """
        licences = self.search([])
        if not licences:
            return False, _("No licence has been entered.")

        licences._refresh_state()
        usable = licences.filtered(lambda l: l.state in ("valid", "expiring"))
        if not usable:
            return False, _("The licence has expired.")

        if module:
            covering = usable.filtered(
                lambda l: module in (l.modules or "").split(", ")
            )
            if not covering:
                return False, _("This licence does not cover %s.") % module
            usable = covering

        over = usable.filtered("over_user_limit")
        if over and len(over) == len(usable):
            return False, _(
                "This licence allows %(allowed)s users and %(actual)s are "
                "active."
            ) % {
                "allowed": over[0].max_users,
                "actual": over[0].active_users,
            }

        return True, usable[0].status_detail or _("Licensed.")

    @api.model
    def require(self, module=None):
        """Like :meth:`check`, but raises. For a module that hard-gates."""
        ok, message = self.check(module)
        if not ok:
            raise UserError(
                _("%(reason)s\n\nContact your supplier to renew or extend the "
                  "licence.") % {"reason": message}
            )
        return True

    @api.model
    def _cron_refresh(self):
        """Keep the status honest as the calendar moves."""
        licences = self.search([])
        licences._refresh_state()
        for licence in licences.filtered(
            lambda l: l.state in ("expiring", "expired")
        ):
            licence.message_post(body=licence.status_detail)
        return len(licences)
