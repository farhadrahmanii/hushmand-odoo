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

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from datetime import date

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
    )
except ImportError:  # pragma: no cover - present wherever licences are issued
    # Not sys.exit. Importing a module must not kill the process: half of this
    # file is module-graph arithmetic that needs no cryptography at all, and
    # the tests for it run in a job that has none installed. Refuse at the
    # point a key is actually touched instead.
    serialization = None
    Ed25519PrivateKey = None


def _require_cryptography():
    if Ed25519PrivateKey is None:
        raise SystemExit(
            "This tool needs the cryptography package to sign or read a key. "
            "Install it with: pip install cryptography"
        )


DEFAULT_KEY_PATH = pathlib.Path.home() / ".hushmand" / "licence_signing_key.pem"


def generate_keys(path):
    """Create a signing keypair and print the public half."""
    _require_cryptography()
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
    _require_cryptography()
    path = pathlib.Path(path)
    if not path.exists():
        sys.exit(
            "No signing key at %s.\nRun with --generate-keys first." % path
        )
    return serialization.load_pem_private_key(path.read_bytes(), password=None)


def licence_closure(modules):
    """Every module of ours the gate will demand, given what was sold.

    A customer who buys af_hr_payroll and receives a licence naming only
    af_hr_payroll cannot use it: the first payslip they create is refused,
    because hm.payslip is declared in hm_payroll and the gate asks for a
    licence covering *that*. The archive already ships the dependency; the
    licence has to cover it too, or the sale fails at their site on the day
    they try it.

    So the list is expanded here rather than left to whoever is typing the
    command at the time.
    """
    import build_release  # noqa: PLC0415  -- same directory, same catalogue

    ours = set(build_release.all_modules())
    unknown = sorted(set(modules) - ours)
    if unknown:
        raise SystemExit(
            "Not modules in this catalogue: %s. Available: %s"
            % (", ".join(unknown), ", ".join(sorted(ours)))
        )
    return build_release.resolve_dependencies(list(modules))


def issue(args):
    private_key = load_private_key(args.key)

    asked = [m.strip() for m in args.modules.split(",") if m.strip()]
    covered = asked if args.exactly else licence_closure(asked)

    payload = {
        "licence_id": args.licence_id or str(uuid.uuid4()),
        "customer": args.customer,
        "modules": covered,
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
    pulled_in = sorted(set(covered) - set(asked))
    if pulled_in:
        print("  of which %s came in as dependencies of what was sold."
              % ", ".join(pulled_in))
        print("           Without them the gate refuses the work the customer")
        print("           actually bought. Price accordingly.")
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
    parser.add_argument("--exactly", action="store_true",
                        help="Cover only the modules named, without the ones "
                             "they depend on. Produces a licence that will "
                             "refuse work the customer paid for; for testing "
                             "the gate, not for selling.")
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
