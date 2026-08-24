# Part of af_jalali. See LICENSE file for full copyright and licensing details.
"""Tests for the pure-Python conversion core.

These import nothing from Odoo, so they also run standalone::

    python tools/run_core_tests.py

Expected values were cross-checked against the reference jalaali
implementation over every day from 1900-01-01 to 2100-12-31.
"""

import datetime
import unittest

from ..core import jalali


class TestJalaliConversion(unittest.TestCase):
    """Known-good anchors, in both directions."""

    ANCHORS = [
        # (gregorian y, m, d), (jalali y, m, d), description
        ((1979, 2, 11), (1357, 11, 22), "Afghan/Iranian historical anchor"),
        ((2000, 1, 1), (1378, 10, 11), "start of the Gregorian millennium"),
        ((2016, 3, 20), (1395, 1, 1), "Nowruz 1395"),
        ((2021, 3, 21), (1400, 1, 1), "Nowruz 1400"),
        ((2024, 3, 20), (1403, 1, 1), "Nowruz 1403, a leap year"),
        ((2026, 3, 21), (1405, 1, 1), "Nowruz 1405"),
        ((2025, 3, 20), (1403, 12, 30), "30 Hoot, only exists in a leap year"),
        ((2025, 3, 19), (1403, 12, 29), "29 Hoot"),
    ]

    def test_to_jalali(self):
        for gregorian, expected, label in self.ANCHORS:
            with self.subTest(label):
                self.assertEqual(tuple(jalali.to_jalali(*gregorian)), expected)

    def test_to_gregorian(self):
        for expected, jalali_date, label in self.ANCHORS:
            with self.subTest(label):
                self.assertEqual(jalali.to_gregorian(*jalali_date), expected)

    def test_round_trip_over_a_century(self):
        """Every day from 1950 to 2050 survives a round trip."""
        day = datetime.date(1950, 1, 1)
        end = datetime.date(2050, 12, 31)
        step = datetime.timedelta(days=1)
        while day <= end:
            jy, jm, jd = jalali.date_to_jalali(day)
            self.assertEqual(jalali.jalali_to_date(jy, jm, jd), day)
            day += step

    def test_consecutive_days_never_skip(self):
        """Consecutive Gregorian days give consecutive Jalali days.

        This is the test that catches a floor-vs-truncate division bug: it
        shows up as a duplicated or skipped day, usually in Hoot or Hamal.
        """
        day = datetime.date(1990, 1, 1)
        end = datetime.date(2060, 12, 31)
        step = datetime.timedelta(days=1)
        previous = jalali.date_to_jalali(day)
        day += step
        while day <= end:
            current = jalali.date_to_jalali(day)
            self.assertNotEqual(current, previous, "duplicate Jalali day at %s" % day)
            previous = current
            day += step


class TestJanuaryFebruaryBoundary(unittest.TestCase):
    """January and February are where truncating division matters.

    ``_div(gm - 8, 6)`` is negative for months 1 and 2. Python's ``//`` floors
    and would shift these dates by a whole year, so they get their own test.
    """

    def test_january(self):
        self.assertEqual(tuple(jalali.to_jalali(2026, 1, 1)), (1404, 10, 11))
        self.assertEqual(tuple(jalali.to_jalali(2026, 1, 31)), (1404, 11, 11))

    def test_february(self):
        self.assertEqual(tuple(jalali.to_jalali(2026, 2, 1)), (1404, 11, 12))
        self.assertEqual(tuple(jalali.to_jalali(2024, 2, 29)), (1402, 12, 10))

    def test_gregorian_leap_day(self):
        """29 February exists only in Gregorian leap years."""
        for year in (2000, 2020, 2024, 2028):
            with self.subTest(year=year):
                jy, jm, jd = jalali.to_jalali(year, 2, 29)
                self.assertEqual(jalali.to_gregorian(jy, jm, jd), (year, 2, 29))


class TestLeapYears(unittest.TestCase):

    LEAP_YEARS = {1395, 1399, 1403, 1408, 1412, 1416}
    COMMON_YEARS = {1396, 1397, 1398, 1400, 1401, 1402, 1404, 1405, 1406, 1407}

    def test_leap_years(self):
        for year in self.LEAP_YEARS:
            with self.subTest(year=year):
                self.assertTrue(jalali.is_leap_jalali_year(year))
                self.assertEqual(jalali.jalali_month_length(year, 12), 30)

    def test_common_years(self):
        for year in self.COMMON_YEARS:
            with self.subTest(year=year):
                self.assertFalse(jalali.is_leap_jalali_year(year))
                self.assertEqual(jalali.jalali_month_length(year, 12), 29)

    def test_month_lengths(self):
        for month in range(1, 7):
            self.assertEqual(jalali.jalali_month_length(1405, month), 31)
        for month in range(7, 12):
            self.assertEqual(jalali.jalali_month_length(1405, month), 30)

    def test_invalid_month(self):
        with self.assertRaises(ValueError):
            jalali.jalali_month_length(1405, 13)


class TestValidation(unittest.TestCase):

    def test_valid(self):
        self.assertTrue(jalali.is_valid_jalali(1405, 6, 2))
        self.assertTrue(jalali.is_valid_jalali(1403, 12, 30))

    def test_invalid(self):
        cases = [
            (1405, 12, 30, "30 Hoot in a common year"),
            (1405, 13, 1, "thirteenth month"),
            (1405, 0, 1, "zeroth month"),
            (1405, 1, 32, "32nd day"),
            (1405, 1, 0, "zeroth day"),
            (1405, 7, 31, "31st of a 30-day month"),
            (9999, 1, 1, "year beyond the supported range"),
        ]
        for jy, jm, jd, label in cases:
            with self.subTest(label):
                self.assertFalse(jalali.is_valid_jalali(jy, jm, jd))

    def test_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            jalali.to_gregorian(4000, 1, 1)
        with self.assertRaises(ValueError):
            jalali.jalali_to_date(1405, 12, 30)


class TestTypeHandling(unittest.TestCase):

    def test_accepts_date(self):
        result = jalali.date_to_jalali(datetime.date(2026, 8, 24))
        self.assertEqual(tuple(result), (1405, 6, 2))

    def test_accepts_datetime(self):
        result = jalali.date_to_jalali(datetime.datetime(2026, 8, 24, 23, 59))
        self.assertEqual(tuple(result), (1405, 6, 2))

    def test_rejects_string(self):
        with self.assertRaises(TypeError):
            jalali.date_to_jalali("2026-08-24")

    def test_named_attributes(self):
        result = jalali.to_jalali(2026, 8, 24)
        self.assertEqual((result.year, result.month, result.day), (1405, 6, 2))


if __name__ == "__main__":
    unittest.main()
