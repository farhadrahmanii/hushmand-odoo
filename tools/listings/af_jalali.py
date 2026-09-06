LISTING = {
    "eyebrow": "Localization",
    "title": "Jalali Calendar for Odoo",
    "lede": "Hijri-Shamsi dates everywhere in Odoo, with the <strong>Afghan</strong> "
            "month names as well as the Iranian ones. Dates stay stored as Gregorian, "
            "so nothing else in your database changes.",
    "callout": (
        "Built for Afghanistan.",
        "Most Jalali modules ship only the Iranian month names, which are wrong on "
        "every Afghan document. This one carries Hamal, Sawr and Jawza alongside "
        "Farvardin, Ordibehesht and Khordad — and Pashto month names too.",
    ),
    "screenshot": "The Jalali settings, per company and overridable per user",
    "blocks": [
        {
            "h2": "Afghan or Iranian, your choice",
            "table": {
                "head": ["Month", "Afghan", "Pashto", "Iranian"],
                # <bdi> keeps each script in its own direction, so the slash
                # between a Latin and an Arabic-script name stays where it was
                # written instead of jumping to the other end of the cell.
                "rows": [
                    ["1", "Hamal / <bdi>حمل</bdi>", "<bdi>وری</bdi>",
                     "Farvardin / <bdi>فروردین</bdi>"],
                    ["2", "Sawr / <bdi>ثور</bdi>", "<bdi>غويی</bdi>",
                     "Ordibehesht / <bdi>اردیبهشت</bdi>"],
                    ["6", "Sunbula / <bdi>سنبله</bdi>", "<bdi>وږی</bdi>",
                     "Shahrivar / <bdi>شهریور</bdi>"],
                ],
            },
        },
        {
            "h2": "What you get",
            "bullets": [
                ("Any date field", 'add <code>widget="jalali_date"</code> and type '
                                   "dates in Jalali"),
                ("Any report", "one <code>t-options</code> attribute prints Jalali"),
                ("Three languages", "English, Dari and Pashto, month and weekday "
                                    "names included"),
                ("Saturday-first week", "matching the Afghan working week"),
                ("Persian numerals", "optional per company"),
                ("Per-user override", "staff working with foreign partners stay on "
                                      "Gregorian"),
                ("Timezone aware", "an evening entry in Kabul does not slip to the "
                                   "day before"),
                ("Nothing migrates", "dates stay Gregorian in the database"),
            ],
        },
        {
            "h2": "Accuracy you can check",
            "text": [
                "Verified against the reference implementation over every single day "
                "from 1900 to 2100 — 73,414 dates — plus every leap year and month "
                "length in between. The screen and the printed page use two separate "
                "implementations, and the test suite diffs them against each other on "
                "every run, so a payslip can never show a different date from the form "
                "it came from.",
                "Supported range: Jalali years −61 to 3177.",
            ],
        },
    ],
    "footer": "Odoo 19.0 · depends on <code>base</code>, <code>base_setup</code> and "
              "<code>web</code> only — no third-party libraries.",
}
