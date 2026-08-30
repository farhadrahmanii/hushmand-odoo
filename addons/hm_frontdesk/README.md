# Front Desk

A visitor register: who is in the building, and who they came to see.

---

## Why this exists

Odoo's Frontdesk is Enterprise, so a Community user has nowhere to record who
came into the building. Most offices fall back to a paper book at the desk,
which answers *“who is here right now?”* only by reading every page.

That is the question asked during a fire drill or an incident — and the one a
paper book answers slowest.

---

## The flow

```
Expected  →  Checked In  →  Checked Out
    ↑            ↓
 registered   host notified
 in advance   on arrival
```

Expected visitors are registered ahead of time and checked in with one click.
Anyone can also be checked in straight from the desk without being expected
first.

---

## What the desk records

| | |
|---|---|
| Visitor and organisation | plus a contact link, if they are already known |
| Host | notified the moment their visitor reaches reception |
| Going to | floor, room or department, so the desk knows where they went |
| ID presented | whatever was shown, and its number |
| Badge and vehicle | for a security desk that issues one and logs the other |
| Accompanying | how many others came in with them |

---

## On Site Now

The list to open during a drill or an incident: who is in the building, their
host and where they went. One screen, and it says plainly when nobody is in the
building rather than showing an empty table.

Minutes on site is computed from the check-in, so a long-running visit is
visible without arithmetic.

---

## Visitors who are never checked out

That is a paper book's usual failure, and the reason a register slowly stops
being trusted. A daily job finds anyone still on site from a previous day and
raises an activity asking their host to confirm when they left.

It does **not** close them automatically. Inventing a departure time nobody
observed would make the register look tidy and be wrong — which is worse than a
record that admits it is incomplete, because the tidy version is the one
somebody would rely on.

Cancelling a visit while the visitor is still on site is refused. Check them
out; they were there.

---

## Compatibility

- Odoo **19.0** Community and Enterprise
- Depends on `mail` and `hm_license`
- Installation instructions: see `af_jalali/INSTALL.md`
