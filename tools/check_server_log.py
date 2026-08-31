#!/usr/bin/env python
"""Fail if Odoo logged anything that is ours while the screens were open.

    python tools/check_server_log.py /tmp/odoo-server.log

A screen can render perfectly and still have thrown server-side: the browser
shows a partial list or an empty table, and the traceback is only in the log.
So the log is read as well as the page.

Known-environmental errors are listed with the reason each one is not ours.
That list is an allowlist and never a blanket filter -- the entire value of
this check is that an error nobody has seen before cannot slip through, so a
new one has to be looked at and then either fixed or explained here.
"""

import pathlib
import re
import sys

#: (fragment, why it is not ours)
IGNORE = [
    ("iap_enrich_auto_done",
     "Odoo core's IAP autocomplete flag races with itself under concurrent "
     "requests, and the ORM retries the write. Core behaviour, made more "
     "likely by CI having no route to Odoo's IAP service. Nothing to do with "
     "these modules."),
]

STAMP = re.compile(r"^[0-9-]+ [0-9:,]+ [0-9]+ ")
ERROR = re.compile(r"^[0-9-]+ [0-9:,]+ [0-9]+ (ERROR|CRITICAL)")


def blocks(lines):
    """Each error line plus the traceback that belongs to it."""
    found = []
    for index, line in enumerate(lines):
        if not ERROR.match(line):
            continue
        end = index + 1
        while end < len(lines) and not STAMP.match(lines[end]):
            end += 1
        found.append(lines[index:end])
    return found


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    path = pathlib.Path(sys.argv[1])
    if not path.is_file():
        raise SystemExit("No log at %s" % path)

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    ignored, real = [], []
    for block in blocks(lines):
        joined = "".join(block)
        reason = next((why for fragment, why in IGNORE if fragment in joined), None)
        (ignored if reason else real).append((block, reason))

    for block, reason in ignored:
        print("ignored: %s" % block[0][:120])
        print("         %s" % reason)

    if real:
        for block, _ in real:
            print("::error::%s" % block[0][:200])
            for line in block[:40]:
                print("  %s" % line)
        print()
        print("%d unexplained error(s) in the server log." % len(real))
        return 1

    print("%d error(s) in the log, all known-environmental." % len(ignored))
    return 0


if __name__ == "__main__":
    sys.exit(main())
