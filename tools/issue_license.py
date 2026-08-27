#!/usr/bin/env python
"""Issue licence keys for the Hushmand Odoo modules.

This is the vendor side of hm_license. It signs a small JSON document with an
Ed25519 private key; the module verifies it with the matching public key, which
is embedded in the addon and safe to publish.

    # once, to create your keypair
    python tools/issue_license.py --generate-keys

    # then, per sale
    python tools/issue_license.py \\
        --customer "Ministry of Rural Development" \\
        --modules af_jalali,af_l10n_base,af_hr \\
        --expires 2027-12-31 \\
        --max-users 40

Keep the private key off this repository and out of any customer's hands. It
is the only thing standing between you and anybody being able to mint their
own licences. A leaked private key means rotating the public key in the addon
and reissuing every licence.
"""

import argparse
import base64
import json
import pathlib
import sys
import uuid
from datetime import date

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
    )
except ImportError:
    sys.exit(
        "This tool needs the cryptography package:\n"
        "    pip install cryptography"
    )

DEFAULT_KEY_PATH = pathlib.Path.home() / ".hushmand" / "licence_signing_key.pem"


def generate_keys(path):
    """Create a signing keypair and print the public half."""
    path = pathlib.Path(path)
    if path.exists():
        sys.exit(
            "%s already exists. Refusing to overwrite it: doing so would "
            "invalidate every licence you have issued." % path
        )

    private_key = Ed25519PrivateKey.generate()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ))
    try:
        path.chmod(0o600)
    except (OSError, NotImplementedError):
        # Windows does not honour POSIX modes; the warning below still stands.
        pass

    public_raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    public_b64 = base64.b64encode(public_raw).decode()

    print("Private key written to %s" % path)
    print("Keep it there. Do not commit it, and do not send it to anyone.\n")
    print("Put this in addons/hm_license/models/hm_license.py:\n")
    print('VENDOR_PUBLIC_KEY = "%s"' % public_b64)


def load_private_key(path):
    path = pathlib.Path(path)
    if not path.exists():
        sys.exit(
            "No signing key at %s.\nRun with --generate-keys first." % path
        )
    return serialization.load_pem_private_key(path.read_bytes(), password=None)


def issue(args):
    private_key = load_private_key(args.key)

    payload = {
        "licence_id": args.licence_id or str(uuid.uuid4()),
        "customer": args.customer,
        "modules": [m.strip() for m in args.modules.split(",") if m.strip()],
        "features": [f.strip() for f in (args.features or "").split(",") if f.strip()],
        "issued": (args.issued or date.today().isoformat()),
        "expires": args.expires,
        "max_users": args.max_users,
    }

    # Signed over a canonical rendering, so re-serialising cannot change the
    # bytes that were signed. The module rebuilds this exactly.
    payload_bytes = json.dumps(
        payload, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    signature = private_key.sign(payload_bytes)

    envelope = {
        "payload": payload,
        "sig": base64.b64encode(signature).decode(),
    }
    key = base64.b64encode(
        json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
    ).decode()

    print("Licence for %s" % payload["customer"])
    print("  id       %s" % payload["licence_id"])
    print("  covers   %s" % ", ".join(payload["modules"]))
    print("  expires  %s" % payload["expires"])
    print("  users    %s" % (payload["max_users"] or "unlimited"))
    print("\nSend the customer everything between the lines.\n")
    print("-" * 68)
    for i in range(0, len(key), 68):
        print(key[i:i + 68])
    print("-" * 68)

    if args.out:
        pathlib.Path(args.out).write_text(key, encoding="utf-8")
        print("\nAlso written to %s" % args.out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generate-keys", action="store_true")
    parser.add_argument("--key", default=str(DEFAULT_KEY_PATH),
                        help="Path to the signing key.")
    parser.add_argument("--customer")
    parser.add_argument("--modules", help="Comma-separated module names.")
    parser.add_argument("--expires", help="YYYY-MM-DD.")
    parser.add_argument("--max-users", type=int, default=0,
                        help="0 for unlimited.")
    parser.add_argument("--features", default="")
    parser.add_argument("--issued", help="Defaults to today.")
    parser.add_argument("--licence-id", help="Defaults to a new UUID.")
    parser.add_argument("--out", help="Also write the key to this file.")
    args = parser.parse_args()

    if args.generate_keys:
        return generate_keys(args.key)

    missing = [
        name for name, value in (
            ("--customer", args.customer),
            ("--modules", args.modules),
            ("--expires", args.expires),
        ) if not value
    ]
    if missing:
        parser.error("required for issuing: %s" % ", ".join(missing))

    try:
        date.fromisoformat(args.expires)
    except ValueError:
        parser.error("--expires must be YYYY-MM-DD")

    return issue(args)


if __name__ == "__main__":
    main()
