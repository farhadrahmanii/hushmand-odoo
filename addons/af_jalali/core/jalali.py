# Part of af_jalali. See LICENSE file for full copyright and licensing details.
"""Gregorian <-> Jalaali (Hijri-Shamsi) calendar conversion.

TIER 0 -- this module imports nothing from Odoo and nothing outside the Python
standard library. It is therefore valid on every Odoo version, and can be used
(and tested) standalone. Do not add Odoo imports here.

Algorithm: the Borkowski / jalaali-js implementation, which is accurate for
Jalaali years -61..3177. It is the same algorithm used by Hushmand ERP's
front-end (``jalali_date/jalaali.js``), so both systems always agree on a date.

Reference: http://www.astro.uni.torun.pl/~kb/Papers/EMP/PersianC-EMP.htm
"""

import datetime

__all__ = [
    "JalaliDate",
    "to_jalali",
    "to_gregorian",
    "is_valid_jalali",
    "is_leap_jalali_year",
    "jalali_month_length",
    "date_to_jalali",
    "jalali_to_date",
    "JALALI_MIN_YEAR",
    "JALALI_MAX_YEAR",
]

JALALI_MIN_YEAR = -61
JALALI_MAX_YEAR = 3177

# Jalaali years that start the 33-year leap cycle.
_BREAKS = (
    -61, 9, 38, 199, 426, 686, 756, 818, 1111, 1181,
    1210, 1635, 2060, 2097, 2192, 2262, 2324, 2394, 2456, 3178,
)


def _div(a, b):
    """Integer division truncated toward zero.

    Python's ``//`` floors, which differs from the reference implementation for
    negative operands (e.g. ``-7 // 6 == -2`` but the algorithm needs ``-1``).
    Getting this wrong silently shifts dates in January and February.
    """
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b > 0) else -q


def _mod(a, b):
    """Remainder matching :func:`_div` (sign follows the dividend)."""
    return a - _div(a, b) * b


class JalaliDate(tuple):
    """An immutable ``(year, month, day)`` triple in the Jalaali calendar."""

    __slots__ = ()

    def __new__(cls, year, month, day):
        return super().__new__(cls, (year, month, day))

    @property
    def year(self):
        return self[0]

    @property
    def month(self):
        return self[1]

    @property
    def day(self):
        return self[2]

    def __repr__(self):
        return "JalaliDate(%d, %d, %d)" % self


def _jal_cal(jy):
    """Leap-year information for a Jalaali year.

    :return: ``(leap, gy, march)`` where ``leap`` is the number of years since
        the last leap year (0 means *this* year is leap), ``gy`` the Gregorian
        year in which the Jalaali year begins, and ``march`` the day of March
        on which 1 Farvardin falls.
    """
    if jy < _BREAKS[0] or jy >= _BREAKS[-1]:
        raise ValueError(
            "Jalaali year %s is out of the supported range %s..%s"
            % (jy, JALALI_MIN_YEAR, JALALI_MAX_YEAR)
        )

    gy = jy + 621
    leap_j = -14
    jp = _BREAKS[0]
    jump = 1

    for jm in _BREAKS[1:]:
        jump = jm - jp
        if jy < jm:
            break
        leap_j += _div(jump, 33) * 8 + _div(_mod(jump, 33), 4)
        jp = jm

    n = jy - jp

    # Leap years from AD 621 to the start of this Jalaali year.
    leap_j += _div(n, 33) * 8 + _div(_mod(n, 33) + 3, 4)
    if _mod(jump, 33) == 4 and jump - n == 4:
        leap_j += 1

    # The same count in the Gregorian calendar.
    leap_g = _div(gy, 4) - _div((_div(gy, 100) + 1) * 3, 4) - 150

    march = 20 + leap_j - leap_g

    if jump - n < 6:
        n = n - jump + _div(jump + 4, 33) * 33
    leap = _mod(_mod(n + 1, 33) - 1, 4)
    if leap == -1:
        leap = 4

    return leap, gy, march


def _g2d(gy, gm, gd):
    """Gregorian date -> Julian Day Number."""
    d = (
        _div((gy + _div(gm - 8, 6) + 100100) * 1461, 4)
        + _div(153 * _mod(gm + 9, 12) + 2, 5)
        + gd
        - 34840408
    )
    return d - _div(_div(gy + 100100 + _div(gm - 8, 6), 100) * 3, 4) + 752


def _d2g(jdn):
    """Julian Day Number -> Gregorian ``(year, month, day)``."""
    j = 4 * jdn + 139361631
    j += _div(_div(4 * jdn + 183187720, 146097) * 3, 4) * 4 - 3908
    i = _div(_mod(j, 1461), 4) * 5 + 308
    gd = _div(_mod(i, 153), 5) + 1
    gm = _mod(_div(i, 153), 12) + 1
    gy = _div(j, 1461) - 100100 + _div(8 - gm, 6)
    return gy, gm, gd


def _j2d(jy, jm, jd):
    """Jalaali date -> Julian Day Number."""
    _leap, gy, march = _jal_cal(jy)
    return _g2d(gy, 3, march) + (jm - 1) * 31 - _div(jm, 7) * (jm - 7) + jd - 1


def _d2j(jdn):
    """Julian Day Number -> Jalaali ``(year, month, day)``."""
    gy = _d2g(jdn)[0]
    jy = gy - 621
    leap, _gy, march = _jal_cal(jy)
    jdn1f = _g2d(gy, 3, march)

    # Days elapsed since 1 Farvardin.
    k = jdn - jdn1f
    if k >= 0:
        if k <= 185:
            # First six months, all 31 days long.
            return jy, 1 + _div(k, 31), _mod(k, 31) + 1
        k -= 186
    else:
        # The date belongs to the previous Jalaali year.
        jy -= 1
        k += 179
        if leap == 1:
            k += 1

    return jy, 7 + _div(k, 30), _mod(k, 30) + 1


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def to_jalali(gy, gm, gd):
    """Convert a Gregorian ``(y, m, d)`` to a :class:`JalaliDate`."""
    return JalaliDate(*_d2j(_g2d(gy, gm, gd)))


def to_gregorian(jy, jm, jd):
    """Convert a Jalaali ``(y, m, d)`` to a Gregorian ``(y, m, d)`` tuple."""
    return _d2g(_j2d(jy, jm, jd))


def is_leap_jalali_year(jy):
    """Is this Jalaali year 366 days long?"""
    return _jal_cal(jy)[0] == 0


def jalali_month_length(jy, jm):
    """Number of days in a Jalaali month.

    Months 1-6 have 31 days, months 7-11 have 30, and Esfand has 29 or 30.
    """
    if not 1 <= jm <= 12:
        raise ValueError("Jalaali month must be 1..12, got %s" % jm)
    if jm <= 6:
        return 31
    if jm <= 11:
        return 30
    return 30 if is_leap_jalali_year(jy) else 29


def is_valid_jalali(jy, jm, jd):
    """Is this a real Jalaali date?"""
    if not JALALI_MIN_YEAR <= jy <= JALALI_MAX_YEAR:
        return False
    if not 1 <= jm <= 12:
        return False
    return 1 <= jd <= jalali_month_length(jy, jm)


def date_to_jalali(value):
    """Convert a :class:`datetime.date` or :class:`datetime.datetime`.

    :return: :class:`JalaliDate`
    """
    if isinstance(value, datetime.datetime):
        value = value.date()
    if not isinstance(value, datetime.date):
        raise TypeError("Expected date or datetime, got %r" % type(value).__name__)
    return to_jalali(value.year, value.month, value.day)


def jalali_to_date(jy, jm, jd):
    """Convert a Jalaali date to :class:`datetime.date`."""
    if not is_valid_jalali(jy, jm, jd):
        raise ValueError("Invalid Jalaali date %s-%s-%s" % (jy, jm, jd))
    return datetime.date(*to_gregorian(jy, jm, jd))
