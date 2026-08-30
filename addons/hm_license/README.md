# Licence Keys

Offline licence verification for commercial Odoo modules.

---

## Why this exists

A paid module needs some way to say what a customer bought and when it lapses.
The usual answer is a licence server, which fails exactly where these modules
are deployed: where the connection is unreliable, and where an ERP that phones
home is a question nobody wants to answer.

A licence here is a small JSON document — who it is for, what it covers, when
it expires, how many users — signed with an Ed25519 private key the vendor
holds. The public key is embedded in this module, and verification happens
entirely on the customer's machine.

**Nothing is sent anywhere.** No server, no telemetry, no connection needed.

**Nothing can be edited into it.** Raising the user limit by hand breaks the
signature and the licence is refused. Every field displayed is read out of the
signed payload rather than typed in.

---

## For the vendor

### Once

```bash
python tools/issue_license.py --generate-keys
```

Put the public half into `VENDOR_PUBLIC_KEY` in
`models/hm_license.py`. **Keep the private half off the repository and off
every customer machine** — it is the only thing preventing anyone from minting
their own licences. A leaked private key means rotating the public key and
reissuing every licence.

### Per sale

```bash
python tools/issue_license.py \
    --customer "Ministry of Rural Development" \
    --modules af_jalali,af_l10n_base,af_hr \
    --expires 2027-12-31 \
    --max-users 40
```

Send the customer the block of text. They paste it whole into
**Settings → Licences**.

`tools/build_release.py` refuses to package anything while the placeholder key
is still in place, so a module cannot ship with the gate disarmed.

---

## The gate

Paid modules inherit `hm.license.gate` on their main document model:

```python
class Payslip(models.Model):
    _name = "hm.payslip"
    _inherit = ["hm.payslip", "hm.license.gate"]

    _licence_module = "hm_payroll"
```

It blocks `create` and `write`. It does **not** block reading, printing,
exporting or unlinking, so an unlicensed database goes read-only in the modules
it has not paid for and keeps every record it already produced.

The gate is inert while the registry is loading — installing or upgrading runs
`create` for every record in a module's data and demo files, long before
anybody could have entered a licence.

### States

| State | Meaning |
|---|---|
| Not Valid | signature failed, or required claims missing |
| Valid | more than 30 days left |
| Expiring Soon | inside 30 days |
| Lapsed — Grace Period | expired, still working, counting down |
| Expired | past the 30-day grace month; new work refused |

`GRACE_DAYS` is 30. A licence that stops a payroll run on the morning it
expires costs the customer far more than the lapse costs the vendor — and the
vendor gets blamed either way.

### Checking it yourself

```python
ok, message = self.env["hm.license"].check("hm_payroll")
self.env["hm.license"].require("hm_payroll")   # raises UserError
```

Both refresh state as `sudo`. An ordinary user has read access to a licence and
nothing more, so a clerk tripping the gate must be told their licence has
lapsed rather than handed an access error about a model they have never heard
of.

---

## What this is not

It is not DRM. Odoo modules ship as readable Python, so a determined person can
edit the check out — equally true of every paid module on the App Store.

The purpose is to make the licence *legible*: the customer sees what they
bought, when it lapses and whether they have outgrown it, and the supplier has
something concrete to point at. Enforcement is contractual.

---

## Compatibility

- Odoo **19.0** Community and Enterprise
- Depends on `mail` only
- Uses the `cryptography` library that ships with Odoo
- Installation instructions: see `af_jalali/INSTALL.md`
