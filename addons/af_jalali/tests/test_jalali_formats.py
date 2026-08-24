# Part of af_jalali. See LICENSE file for full copyright and licensing details.
"""Tests for formatting and parsing. No Odoo imports -- see test_jalali_core."""

import datetime
import unittest

from ..core import formats


class TestFormatting(unittest.TestCase):

    # 24 August 2026 is a Monday, and 2 Sunbula 1405.
    DATE = datetime.date(2026, 8, 24)

    def test_default_pattern(self):
        self.assertEqual(formats.format_jalali(self.DATE), "1405/06/02")

    def test_afghan_month_names(self):
        self.assertEqual(
            formats.format_jalali(self.DATE, "dd MMMM yyyy"), "02 Sunbula 1405"
        )

    def test_iranian_month_names_differ(self):
        """The whole reason the scheme is a setting."""
        afghan = formats.format_jalali(self.DATE, "MMMM", scheme=formats.SCHEME_AFGHAN)
        iranian = formats.format_jalali(self.DATE, "MMMM", scheme=formats.SCHEME_IRANIAN)
        self.assertEqual(afghan, "Sunbula")
        self.assertEqual(iranian, "Shahrivar")
        self.assertNotEqual(afghan, iranian)

    def test_dari_and_pashto_month_names_differ(self):
        dari = formats.month_name(6, formats.SCHEME_AFGHAN, "fa")
        pashto = formats.month_name(6, formats.SCHEME_AFGHAN, "ps")
        self.assertEqual(dari, "سنبله")
        self.assertEqual(pashto, "وږی")

    def test_weekday_is_saturday_first(self):
        """Saturday is index 0, because the Afghan week starts there."""
        saturday = datetime.date(2026, 8, 22)
        self.assertEqual(formats.weekday_index(saturday), 0)
        self.assertEqual(formats.weekday_name(saturday), "Shanbe")
        self.assertEqual(formats.weekday_name(self.DATE), "Doshanbe")

    def test_all_tokens(self):
        moment = datetime.datetime(2026, 8, 24, 14, 5, 9)
        self.assertEqual(formats.format_jalali(moment, "yyyy"), "1405")
        self.assertEqual(formats.format_jalali(moment, "yy"), "05")
        self.assertEqual(formats.format_jalali(moment, "MM"), "06")
        self.assertEqual(formats.format_jalali(moment, "M"), "6")
        self.assertEqual(formats.format_jalali(moment, "dd"), "02")
        self.assertEqual(formats.format_jalali(moment, "d"), "2")
        self.assertEqual(formats.format_jalali(moment, "MMM"), "Sun")
        self.assertEqual(formats.format_jalali(moment, "HH:mm:ss"), "14:05:09")

    def test_quoted_literal_text(self):
        self.assertEqual(
            formats.format_jalali(self.DATE, "'Issued on' dd/MM/yyyy"),
            "Issued on 02/06/1405",
        )

    def test_unquoted_letters_are_consumed_as_tokens(self):
        """Documented behaviour, and the reason literals must be quoted.

        The ``ss`` and ``d`` inside "Issued" are real tokens. Quoting is the
        ICU convention and the only correct way to embed words.
        """
        self.assertNotEqual(
            formats.format_jalali(self.DATE, "Issued on dd"), "Issued on 02"
        )

    def test_escaped_apostrophe(self):
        self.assertEqual(
            formats.format_jalali(self.DATE, "'Farhad''s date:' yyyy"),
            "Farhad's date: 1405",
        )

    def test_separators_need_no_quoting(self):
        for pattern, expected in [
            ("yyyy/MM/dd", "1405/06/02"),
            ("dd-MM-yyyy", "02-06-1405"),
            ("dd MMMM yyyy", "02 Sunbula 1405"),
        ]:
            with self.subTest(pattern):
                self.assertEqual(formats.format_jalali(self.DATE, pattern), expected)

    def test_eastern_digits(self):
        self.assertEqual(
            formats.format_jalali(self.DATE, eastern_digits=True), "۱۴۰۵/۰۶/۰۲"
        )

    def test_empty_value(self):
        self.assertEqual(formats.format_jalali(None), "")

    def test_rejects_string_input(self):
        with self.assertRaises(TypeError):
            formats.format_jalali("2026-08-24")


class TestParsing(unittest.TestCase):

    EXPECTED = datetime.date(2026, 8, 24)

    def test_separators(self):
        for text in ("1405/06/02", "1405-06-02", "1405.6.2", "1405 06 02"):
            with self.subTest(text):
                self.assertEqual(formats.parse_jalali(text), self.EXPECTED)

    def test_eastern_digits(self):
        self.assertEqual(formats.parse_jalali("۱۴۰۵/۰۶/۰۲"), self.EXPECTED)
        self.assertEqual(formats.parse_jalali("١٤٠٥/٠٦/٠٢"), self.EXPECTED)

    def test_month_names(self):
        for text in ("2 Sunbula 1405", "1405 Sunbula 2", "2 سنبله 1405", "2 وږی 1405"):
            with self.subTest(text):
                self.assertEqual(formats.parse_jalali(text), self.EXPECTED)

    def test_iranian_month_name_also_accepted(self):
        """Parsing is permissive even when the display scheme is Afghan."""
        self.assertEqual(formats.parse_jalali("2 Shahrivar 1405"), self.EXPECTED)

    def test_round_trip(self):
        self.assertEqual(
            formats.parse_jalali(formats.format_jalali(self.EXPECTED)), self.EXPECTED
        )

    def test_invalid_input(self):
        cases = ["", "not a date", "1405/13/01", "1405/12/30", "1405/1", "1405/1/99"]
        for text in cases:
            with self.subTest(text):
                with self.assertRaises(ValueError):
                    formats.parse_jalali(text)

    def test_unknown_month_name(self):
        with self.assertRaises(ValueError):
            formats.parse_jalali("2 Brumaire 1405")


class TestDigitHelpers(unittest.TestCase):

    def test_to_latin(self):
        self.assertEqual(formats.to_latin_digits("۱۴۰۵"), "1405")
        self.assertEqual(formats.to_latin_digits("١٤٠٥"), "1405")
        self.assertEqual(formats.to_latin_digits("1405"), "1405")

    def test_to_eastern(self):
        self.assertEqual(formats.to_eastern_digits("1405"), "۱۴۰۵")

    def test_non_digits_untouched(self):
        self.assertEqual(formats.to_latin_digits("Sunbula ۲"), "Sunbula 2")


if __name__ == "__main__":
    unittest.main()
