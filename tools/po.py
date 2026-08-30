# Part of the Hushmand Odoo addons tooling.
"""A small PO/POT reader and writer.

Only what this repository needs: read the entries out of a template, and write
a translation file that keeps the template's comments and ordering. gettext
tooling is not installed in CI and `polib` is not a dependency worth adding for
two hundred lines of string handling.

An entry is a comment block, a msgid and a msgstr. Everything before the first
blank-line-separated block is the header, which is copied through untouched
apart from the language fields.
"""

import re

#: PO escapes exactly these, and encodes newlines and tabs.
_ESCAPES = [
    ("\\", "\\\\"),
    ('"', '\\"'),
    ("\t", "\\t"),
    ("\n", "\\n"),
]

_STRING_LINE = re.compile(r'^"(.*)"$')


class Entry:
    """One translatable term, with the comments that explain where it lives."""

    def __init__(self, comments, msgid, msgstr=""):
        self.comments = comments
        self.msgid = msgid
        self.msgstr = msgstr

    @property
    def is_header(self):
        return self.msgid == ""

    @property
    def references(self):
        """The `#:` lines, which say which file the term came from."""
        return [c[3:] for c in self.comments if c.startswith("#: ")]

    def is_python_format(self):
        """Whether the term carries %s or %(name)s placeholders.

        A translation that drops one of these raises at render time in the
        customer's face, so it is worth checking rather than trusting.
        """
        return bool(re.search(r"%(?:\([^)]+\))?[sdfr]|%%", self.msgid))


def unescape(text):
    out = []
    i = 0
    while i < len(text):
        char = text[i]
        if char == "\\" and i + 1 < len(text):
            nxt = text[i + 1]
            out.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(nxt, nxt))
            i += 2
        else:
            out.append(char)
            i += 1
    return "".join(out)


def escape(text):
    for plain, escaped in _ESCAPES:
        text = text.replace(plain, escaped)
    return text


def _collect(lines, start):
    """Read one msgid/msgstr value, which may continue over several lines."""
    parts = []
    first = lines[start].split(" ", 1)
    if len(first) > 1:
        match = _STRING_LINE.match(first[1].strip())
        if match:
            parts.append(match.group(1))
    index = start + 1
    while index < len(lines):
        match = _STRING_LINE.match(lines[index].strip())
        if not match:
            break
        parts.append(match.group(1))
        index += 1
    return unescape("".join(parts)), index


def parse(path):
    """Read a .po or .pot file into a list of :class:`Entry`."""
    lines = path.read_text(encoding="utf-8").split("\n")
    entries = []
    comments = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if line.startswith("#"):
            comments.append(line)
            index += 1
            continue
        if line.startswith("msgid "):
            msgid, index = _collect(lines, index)
            msgstr = ""
            if index < len(lines) and lines[index].startswith("msgstr "):
                msgstr, index = _collect(lines, index)
            entries.append(Entry(comments, msgid, msgstr))
            comments = []
            continue
        index += 1
    return entries


def _render_value(keyword, value):
    """Render `msgid`/`msgstr`, splitting multi-line text the way Odoo does."""
    if "\n" not in value:
        return ['%s "%s"' % (keyword, escape(value))]
    # Keep the trailing newline attached to the line it ends, so the file
    # reads the way the source string does.
    pieces = value.split("\n")
    rendered = ['%s ""' % keyword]
    for position, piece in enumerate(pieces):
        if position < len(pieces) - 1:
            rendered.append('"%s\\n"' % escape(piece))
        elif piece:
            rendered.append('"%s"' % escape(piece))
    return rendered


def write(path, entries):
    """Write entries back out, comments and order preserved."""
    out = []
    for entry in entries:
        out.extend(entry.comments)
        out.extend(_render_value("msgid", entry.msgid))
        out.extend(_render_value("msgstr", entry.msgstr))
        out.append("")
    path.write_text("\n".join(out), encoding="utf-8")


def header(language, module_names):
    """A PO header for a translation this repository ships."""
    body = "\n".join([
        "Project-Id-Version: Odoo Server 19.0",
        "Report-Msgid-Bugs-To: ",
        "Last-Translator: ",
        "Language-Team: ",
        "MIME-Version: 1.0",
        "Content-Type: text/plain; charset=UTF-8",
        "Content-Transfer-Encoding: 8bit",
        "Language: %s" % language,
        "Plural-Forms: nplurals=2; plural=(n > 1);",
        "",
    ])
    comments = [
        "# Translation of Odoo Server.",
        "# This file contains the translation of the following modules:",
    ] + ["# \t* %s" % name for name in module_names] + ["#"]
    return Entry(comments, "", body)
