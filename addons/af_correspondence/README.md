# Correspondence Register (Maktoob)

What came in, what went out, its number, who it was from and who has to deal
with it.

---

## Why this exists

Every Afghan office keeps a bound register of official letters. When a ministry
asks what happened to a letter, the register is what gets consulted.

Odoo has no concept of it, and attaching a scan to a contact loses the part
that matters — **the sequence**. Numbers are issued in order, and a gap in the
outgoing numbers is a question somebody has to answer.

---

## Two independent series

Incoming and outgoing are numbered separately, the way a paper register keeps
two books.

The direction **cannot be changed** once a letter is registered, because its
number came from that series. Cancel it and register a new one — which is
exactly what happens with paper, and for the same reason.

---

## Dates and references, kept apart

| Field | What it is |
|---|---|
| Register number | issued in order by the series; not editable |
| Register date | when it was entered in the book |
| Letter date | the date written on the letter itself |
| Their reference | the number the other office put on it |

A letter written on the 1st may not arrive until the 10th. Collapsing those
into one date loses the delay, which is often the thing being asked about.

---

## A correspondent who need not be a contact

A one-off letter from a district office does not justify creating a partner
record. Set the correspondent as free text and the register is still complete;
link a contact when there is one worth keeping.

---

## So a letter is not lost

```
Registered  →  In Progress  →  Answered  →  Closed
                     ↓
                 Cancelled
```

- **Assignment.** An incoming letter nobody owns is a letter nobody answers.
- **A reply-by date**, with overdue letters filterable — before the ministry
  rings.
- **Replies link back** to the letter they answer, so a thread stays intact and
  readable years later. Drafting a reply carries the subject across as
  *Re: …* and links the two.
- **The scan attached** to the register entry, so the letter can always be
  found again.

---

## The register is a record

A closed letter cannot be cancelled. What happened, happened — and a register
that can be tidied up afterwards is not a register anybody can rely on when the
question finally comes.

---

## Compatibility

- Odoo **19.0** Community and Enterprise
- Depends on `mail` and `hm_license`
- Prints Hijri-Shamsi dates if `af_jalali` is installed
- Installation instructions: see `af_jalali/INSTALL.md`
