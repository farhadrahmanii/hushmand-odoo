# Zakat Administration

Collect, hold and distribute zakat, with a record that reconciles.

---

## Why this exists

Zakat is not an expense. It is an obligation calculated on wealth, collected
into a fund, and distributed to people who qualify under defined categories. An
organisation administering it has to be able to show what came in, who received
what, and that the two reconcile.

Recording it as ordinary expenses loses the part that matters: the link between
what was collected and what it paid for.

---

## Two rules the software enforces

### Nothing is distributed that was never collected

Marking a distribution as paid is refused if it exceeds what the fund actually
holds. A **pledge does not raise that limit**, because a pledge is not money —
only received contributions count towards what can be given out.

### A fund cannot be closed over an undistributed balance

Zakat collected and not yet given out is owed to beneficiaries, not held by the
organisation. Closing the books on it is refused until it is distributed or
carried into another fund.

---

## The fund

| Figure | Meaning |
|---|---|
| Collected | contributions actually received |
| Distributed | paid out |
| Undistributed | still held, and owed to beneficiaries |

The three reconcile at all times, which is what makes the fund something you
can show a donor.

---

## Beneficiaries

Recorded against the eight categories of eligible recipient, with the
assessment of why the person qualifies and who verified it — kept on the record
rather than in somebody's memory.

Each beneficiary carries how many times they have been helped, how much in
total, and when they last received something — **across every fund**, not just
the one in front of you.

That is what stops a well-known family being assisted three times while a
street away somebody is missed, which is the failure that quietly discredits a
distribution programme.

---

## Contributions

Cash, bank transfer or in kind. What was actually handed over is recorded when
it was not money.

Zakat is often given without the giver being named. Marking a contribution
anonymous keeps the record and hides only the name.

---

## Distributions

```
Planned  →  Paid
```

Paying checks the fund balance first. The record keeps what was given, to whom,
where, and whether the beneficiary **signed for it** — and the absence of a
signed receipt is searchable, because that is what an audit asks for.

---

## Compatibility

- Odoo **19.0** Community and Enterprise
- Depends on `mail`, `af_l10n_base` and `hm_license`
- Installation instructions: see `af_jalali/INSTALL.md`
