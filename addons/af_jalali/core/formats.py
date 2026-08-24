# Part of af_jalali. See LICENSE file for full copyright and licensing details.
"""Formatting and parsing of Jalaali dates, in Afghan and Iranian conventions.

TIER 0 -- no Odoo imports. See :mod:`core.jalali`.

Afghanistan and Iran share the Solar Hijri calendar but *not* the month names.
Afghanistan uses the zodiacal names (Hamal, Sawr, Jawza...) while Iran uses the
Zoroastrian ones (Farvardin, Ordibehesht, Khordad...). A module shipping only
the Iranian names is wrong for every Afghan user, so both are supported and the
scheme is a setting.
"""

import datetime
import re

from . import jalali

__all__ = [
    "SCHEME_AFGHAN",
    "SCHEME_IRANIAN",
    "MONTH_NAMES",
    "WEEKDAY_NAMES",
    "DEFAULT_FORMAT",
    "format_jalali",
    "parse_jalali",
    "to_latin_digits",
    "to_eastern_digits",
    "month_name",
    "weekday_name",
    "weekday_index",
]

SCHEME_AFGHAN = "afghan"
SCHEME_IRANIAN = "iranian"

#: Month names by scheme, then by language.
MONTH_NAMES = {
    SCHEME_AFGHAN: {
        "en": [
            "Hamal", "Sawr", "Jawza", "Saratan", "Asad", "Sunbula",
            "Mizan", "Aqrab", "Qaws", "Jadi", "Dalwa", "Hoot",
        ],
        "fa": [
            "حمل", "ثور", "جوزا", "سرطان", "اسد", "سنبله",
            "میزان", "عقرب", "قوس", "جدی", "دلو", "حوت",
        ],
        "ps": [
            "وری", "غويی", "غبرګولی", "چنګاښ", "زمری", "وږی",
            "تله", "لړم", "لیندۍ", "مرغومی", "سلواغه", "کب",
        ],
    },
    SCHEME_IRANIAN: {
        "en": [
            "Farvardin", "Ordibehesht", "Khordad", "Tir", "Mordad", "Shahrivar",
            "Mehr", "Aban", "Azar", "Dey", "Bahman", "Esfand",
        ],
        "fa": [
            "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
            "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
        ],
    },
}

#: Weekday names, Saturday first -- the Afghan working week starts on Saturday.
WEEKDAY_NAMES = {
    "en": ["Shanbe", "Yakshanbe", "Doshanbe", "Seshanbe",
           "Chaharshanbe", "Panjshanbe", "Juma"],
    "fa": ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه",
           "چهارشنبه", "پنجشنبه", "جمعه"],
    "ps": ["شنبه", "یکشنبه", "دوشنبه", "درېشنبه",
           "څلورشنبه", "پنجشنبه", "جمعه"],
}

#: Default output pattern. Tokens are documented on :func:`format_jalali`.
DEFAULT_FORMAT = "yyyy/MM/dd"

_PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
_ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_LATIN_DIGITS = "0123456789"

_TO_LATIN = {ord(c): _LATIN_DIGITS[i] for i, c in enumerate(_PERSIAN_DIGITS)}
_TO_LATIN.update({ord(c): _LATIN_DIGITS[i] for i, c in enumerate(_ARABIC_DIGITS)})
_TO_EASTERN = {ord(c): _PERSIAN_DIGITS[i] for i, c in enumerate(_LATIN_DIGITS)}

# Longest tokens first, so that yyyy is not consumed as two yy.
_TOKEN_RE = re.compile(r"yyyy|yy|MMMM|MMM|MM|M|dd|d|EEEE|EEE|HH|H|mm|ss")

# Text between single quotes is literal, so "'Issued on' dd/MM/yyyy" does not
# lose the "ss" and "d" out of the word "Issued". Two quotes mean one quote.
# This is the ICU convention, which Babel and Java also use.
_QUOTED_RE = re.compile(r"'((?:[^']|'')*)'")

_SEPARATORS = re.compile(r"[/\-.\s،]+")


def to_latin_digits(text):
    """Normalise Persian and Arabic-Indic digits to ASCII."""
    return str(text).translate(_TO_LATIN)


def to_eastern_digits(text):
    """Render ASCII digits as Persian (Eastern Arabic) digits."""
    return str(text).translate(_TO_EASTERN)


def _names(mapping, lang, fallback="en"):
    if lang in mapping:
        return mapping[lang]
    # Pashto falls back to Dari, which is closer than English.
    if lang == "ps" and "fa" in mapping:
        return mapping["fa"]
    return mapping[fallback]


def month_name(month, scheme=SCHEME_AFGHAN, lang="en"):
    """Name of a Jalaali month (1-12)."""
    if not 1 <= month <= 12:
        raise ValueError("Jalaali month must be 1..12, got %s" % month)
    scheme_names = MONTH_NAMES.get(scheme, MONTH_NAMES[SCHEME_AFGHAN])
    return _names(scheme_names, lang)[month - 1]


def weekday_index(value):
    """Index of a Gregorian date in the Afghan week (0 = Saturday)."""
    if isinstance(value, datetime.datetime):
        value = value.date()
    # datetime.weekday(): Monday is 0 ... Sunday is 6, so Saturday is 5.
    return (value.weekday() + 2) % 7


def weekday_name(value, lang="en"):
    """Weekday name for a Gregorian date, in the Saturday-first week."""
    return _names(WEEKDAY_NAMES, lang)[weekday_index(value)]


def format_jalali(value, fmt=DEFAULT_FORMAT, scheme=SCHEME_AFGHAN, lang="en",
                  eastern_digits=False):
    """Format a Gregorian date or datetime as a Jalaali string.

    Supported tokens:

    ==============  ===============================================
    ``yyyy``        Jalaali year, four digits (1405)
    ``yy``          Jalaali year, two digits (05)
    ``MMMM``        Month name (Sunbula)
    ``MMM``         Month name, abbreviated to three characters
    ``MM``          Month number, zero padded (06)
    ``M``           Month number (6)
    ``dd``          Day, zero padded (02)
    ``d``           Day (2)
    ``EEEE``        Weekday name (Yakshanbe)
    ``HH mm ss``    Time components, zero padded
    ==============  ===============================================

    Separators are copied through, so both ``dd MMMM yyyy`` and
    ``yyyy/MM/dd HH:mm`` work as written.

    **Literal words must be quoted.** Letters that spell a token are otherwise
    consumed as one: ``"Issued on dd"`` would render as ``"Iue2 on 02"``
    because of the ``ss`` and the ``d``. Wrap literal text in single quotes,
    the ICU convention::

        format_jalali(day, "'Issued on' dd/MM/yyyy")   # Issued on 02/06/1405

    Use ``''`` for a literal apostrophe.

    :param eastern_digits: render digits as Persian numerals.
    """
    if value is None:
        return ""

    if isinstance(value, datetime.datetime):
        date_part, time_part = value.date(), value
    elif isinstance(value, datetime.date):
        date_part, time_part = value, None
    else:
        raise TypeError("Expected date or datetime, got %r" % type(value).__name__)

    jy, jm, jd = jalali.date_to_jalali(date_part)

    def replace(match):
        token = match.group(0)
        if token == "yyyy":
            return "%04d" % jy
        if token == "yy":
            return "%02d" % (jy % 100)
        if token == "MMMM":
            return month_name(jm, scheme, lang)
        if token == "MMM":
            return month_name(jm, scheme, lang)[:3]
        if token == "MM":
            return "%02d" % jm
        if token == "M":
            return str(jm)
        if token == "dd":
            return "%02d" % jd
        if token == "d":
            return str(jd)
        if token in ("EEEE", "EEE"):
            name = weekday_name(date_part, lang)
            return name if token == "EEEE" else name[:3]
        if time_part is None:
            return ""
        if token == "HH":
            return "%02d" % time_part.hour
        if token == "H":
            return str(time_part.hour)
        if token == "mm":
            return "%02d" % time_part.minute
        if token == "ss":
            return "%02d" % time_part.second
        return token

    # Substitute tokens only outside quoted literals.
    pieces, position = [], 0
    for quoted in _QUOTED_RE.finditer(fmt):
        pieces.append(_TOKEN_RE.sub(replace, fmt[position:quoted.start()]))
        pieces.append(quoted.group(1).replace("''", "'"))
        position = quoted.end()
    pieces.append(_TOKEN_RE.sub(replace, fmt[position:]))

    result = "".join(pieces)
    return to_eastern_digits(result) if eastern_digits else result


def _expand_year(jy):
    """Turn a two-digit year into a four-digit one in the current century."""
    if jy >= 100:
        return jy
    current = jalali.date_to_jalali(datetime.date.today()).year
    return (current // 100) * 100 + jy


def _month_from_name(token):
    """Resolve a month name in any scheme or language to its number."""
    needle = token.strip().lower()
    for scheme_names in MONTH_NAMES.values():
        for names in scheme_names.values():
            for index, name in enumerate(names):
                lowered = name.lower()
                if lowered == needle or lowered.startswith(needle):
                    return index + 1
    return None


def parse_jalali(text, scheme=SCHEME_AFGHAN, lang="en"):
    """Parse a Jalaali date string into a :class:`datetime.date`.

    Accepts ``1405/06/02``, ``1405-06-02``, ``1405.6.2``, Persian digits, and
    month names in any supported language or scheme (``2 Sunbula 1405``).

    :raises ValueError: if the text is not a valid Jalaali date.
    """
    if not text:
        raise ValueError("Empty Jalaali date")

    raw = to_latin_digits(str(text).strip())
    parts = [p for p in _SEPARATORS.split(raw) if p]
    if len(parts) < 3:
        raise ValueError("Cannot parse Jalaali date %r" % text)

    # A month name may appear in any position, so resolve it to a number first.
    numbers, month_from_name = [], None
    for part in parts[:4]:
        if part.isdigit():
            numbers.append(int(part))
            continue
        resolved = _month_from_name(part)
        if resolved is None:
            raise ValueError("Unknown month name %r in %r" % (part, text))
        month_from_name = resolved

    if month_from_name is not None:
        if len(numbers) < 2:
            raise ValueError("Cannot parse Jalaali date %r" % text)
        # "2 Sunbula 1405" is day first, "1405 Sunbula 2" is year first.
        if numbers[0] > 31:
            jy, jd = numbers[0], numbers[1]
        else:
            jd, jy = numbers[0], numbers[1]
        jm = month_from_name
    else:
        if len(numbers) < 3:
            raise ValueError("Cannot parse Jalaali date %r" % text)
        jy, jm, jd = numbers[0], numbers[1], numbers[2]

    jy = _expand_year(jy)
    if not jalali.is_valid_jalali(jy, jm, jd):
        raise ValueError("Invalid Jalaali date %r" % text)
    return jalali.jalali_to_date(jy, jm, jd)
