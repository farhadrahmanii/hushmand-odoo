# Shift Rosters

Schedule guards, drivers or a reception desk, and be told when the roster is
broken.

---

## Why this exists

Odoo Planning is Enterprise, so a Community user scheduling shift workers has
nothing. The usual fallback is a spreadsheet per month, and it always fails the
same two ways: somebody ends up on two shifts at once, or a night nobody is
covering goes unnoticed until it is that night.

Both are checked here, at the moment they happen rather than on the night.

---

## Double-booking is refused outright

Assigning somebody to overlapping shifts raises an error as it happens, naming
the shift they are already on and its times.

---

## Publishing with gaps takes a second action

A roster with unassigned shifts is exactly what gets published by accident. The
normal **Publish** button refuses and says how many shifts are uncovered.
**Publish With Gaps** does it anyway, for when the gap is known and accepted.

```
Draft  →  Published  →  Closed
```

A closed roster cannot be reopened. Copy it instead — which is also how next
month usually starts.

---

## Night shifts are handled properly

A shift from 18:00 to 06:00 ends on the **following day**. The hours are real
datetimes rather than a pair of clock times that quietly compute a negative
duration, which is the bug every hand-built roster spreadsheet has.

Tick *Ends Next Day* on the template and the end datetime is built correctly
every time the shift is used.

---

## Shift templates

The patterns you use over and over:

| Template | Hours | Ends next day |
|---|---|---|
| Day | 08:00 – 16:00 | no |
| Night | 18:00 – 06:00 | yes |

Building a month then means choosing a shift and a person rather than typing
times. The hours come from the template and can still be overridden on the day
it matters.

A colour on the template carries through to the calendar, so a month reads at a
glance.

---

## What the roster tells you

- **Uncovered** — shifts with nobody on them, as a filter and a count.
- Shifts outside the roster period are refused, so a date typed wrong does not
  silently land in another month.
- The roster names the gate, building or site it covers, because most
  organisations run more than one.

---

## Compatibility

- Odoo **19.0** Community and Enterprise
- Depends on `hr`, `mail` and `hm_license`
- Installation instructions: see `af_jalali/INSTALL.md`
