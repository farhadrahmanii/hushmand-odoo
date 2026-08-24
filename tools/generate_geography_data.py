#!/usr/bin/env python
"""Generate af_l10n_base geography data files from the extracted JSON.

Source: tools/data/af_geography.json, extracted from the Hushmand ERP
production database (34 provinces, 546 districts, trilingual).

    python tools/generate_geography_data.py

Writes:
    addons/af_l10n_base/data/res_country_state_data.xml
    addons/af_l10n_base/data/af_district_data.xml

Provinces become res.country.state records so they plug into Odoo's own
address system: every partner, employee and invoice address gets province
support with no extra work. They carry the published ISO 3166-2:AF codes,
so the data is interoperable with anything else that speaks ISO.

Re-running is safe. XML ids are derived from the ISO code (provinces) and
the source row id (districts), so records update in place rather than
duplicating.
"""

import json
import pathlib
import sys
from xml.sax.saxutils import escape

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools" / "data" / "af_geography.json"
DATA_DIR = ROOT / "addons" / "af_l10n_base" / "data"

# Hushmand ERP province name -> ISO 3166-2:AF code.
# Verified against the published ISO 3166-2:AF list; all 34 map one to one.
ISO_CODES = {
    "KABUL": "KAB",
    "KAPISA": "KAP",
    "PARWAN": "PAR",
    "WARDAK": "WAR",          # ISO name: Maidan Wardak
    "LOGAR": "LOG",
    "NANGARHAR": "NAN",
    "LAGHMAN": "LAG",
    "PANJSHER": "PAN",        # ISO name: Panjshir
    "BAGHLAN": "BGL",
    "BAMYAN": "BAM",
    "GHAZNI": "GHA",
    "PAKTIKA": "PKA",
    "PAKTYA": "PIA",          # ISO name: Paktia
    "KHOST": "KHO",
    "KUNARHA": "KNR",         # ISO name: Kunar
    "NOORISTAN": "NUR",       # ISO name: Nuristan
    "BADAKHSHAN": "BDS",
    "TAKHAR": "TAK",
    "KUNDUZ": "KDZ",
    "SAMANGAN": "SAM",
    "BALKH": "BAL",
    "SAR-E-PUL": "SAR",       # ISO name: Sar-e Pol
    "GHOR": "GHO",
    "DAYKUNDI": "DAY",
    "UROZGAN": "URU",
    "ZABUL": "ZAB",
    "KANDAHAR": "KAN",
    "JAWZJAN": "JOW",
    "FARYAB": "FYB",
    "HELMAND": "HEL",
    "BADGHIS": "BDG",
    "HERAT": "HER",
    "FARAH": "FRA",
    "NIMROZ": "NIM",
}

# The database stores names in shouting capitals. Title case reads better on
# an invoice, but a few need help: SAR-E-PUL should not become Sar-E-Pul.
TITLE_OVERRIDES = {
    "SAR-E-PUL": "Sar-e Pol",
    "KUNARHA": "Kunar",
    "NOORISTAN": "Nuristan",
    "PANJSHER": "Panjshir",
    "PAKTYA": "Paktia",
    "WARDAK": "Maidan Wardak",
    "UROZGAN": "Urozgan",
    "NIMROZ": "Nimruz",
    "DAYKUNDI": "Daykundi",
}

HEADER = """<?xml version="1.0" encoding="utf-8"?>
<!-- GENERATED FILE - do not edit by hand.
     Regenerate with: python tools/generate_geography_data.py
     Source: tools/data/af_geography.json (Hushmand ERP production data) -->
<odoo noupdate="1">
"""

FOOTER = "</odoo>\n"


def title_case(name):
    """Turn a shouted province or district name into something printable."""
    name = name.strip()
    if name.upper() in TITLE_OVERRIDES:
        return TITLE_OVERRIDES[name.upper()]
    # Title-case each word but keep the hyphen and apostrophe joins readable.
    words = []
    for word in name.split():
        if "-" in word:
            words.append("-".join(p.capitalize() for p in word.split("-")))
        else:
            words.append(word.capitalize())
    return " ".join(words)


def field(name, value):
    if value is None or value == "":
        return ""
    return '            <field name="%s">%s</field>\n' % (name, escape(str(value)))


def generate_provinces(provinces):
    lines = [HEADER]
    seen_codes = set()

    for province in provinces:
        source_name = province["en"].strip().upper()
        code = ISO_CODES.get(source_name)
        if not code:
            raise SystemExit(
                "No ISO code mapped for province %r. Add it to ISO_CODES."
                % source_name
            )
        if code in seen_codes:
            raise SystemExit("Duplicate ISO code %s" % code)
        seen_codes.add(code)

        xml_id = "state_af_%s" % code.lower()
        lines.append('        <record id="%s" model="res.country.state">\n' % xml_id)
        lines.append('            <field name="country_id" ref="base.af"/>\n')
        lines.append(field("name", title_case(province["en"])))
        lines.append(field("code", code))
        lines.append(field("af_name_dr", province.get("dr")))
        lines.append(field("af_name_ps", province.get("pa")))
        lines.append("        </record>\n")

    lines.append(FOOTER)
    return "".join(lines), seen_codes


def generate_districts(districts, provinces):
    by_id = {p["id"]: p for p in provinces}
    lines = [HEADER]
    count = 0
    filled_from_dari = []

    for district in districts:
        province = by_id.get(district["province_id"])
        if province is None:
            # Districts of the UNKNOWN province were filtered at extraction.
            continue
        code = ISO_CODES[province["en"].strip().upper()]

        # The xml id uses the source row id, so re-running the generator
        # updates records in place instead of creating duplicates.
        # The source data has one district (Delaram, in Nimruz) with no Pashto
        # name. Falling back to the Dari name here beats shipping a blank, and
        # beats editing the source database. The count is reported so the gap
        # stays visible rather than quietly papered over.
        name_dr = district.get("dr") or ""
        name_ps = district.get("pa") or ""
        if not name_ps and name_dr:
            name_ps = name_dr
            filled_from_dari.append(district["en"])

        xml_id = "district_af_%s" % district["id"]
        lines.append('        <record id="%s" model="af.district">\n' % xml_id)
        lines.append(
            '            <field name="state_id" ref="state_af_%s"/>\n' % code.lower()
        )
        lines.append(field("name", title_case(district["en"])))
        lines.append(field("name_dr", name_dr))
        lines.append(field("name_ps", name_ps))
        lines.append("        </record>\n")
        count += 1

    lines.append(FOOTER)
    return "".join(lines), count, filled_from_dari


def main():
    if not SOURCE.is_file():
        raise SystemExit("Missing %s" % SOURCE)

    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    provinces = payload["provinces"]
    districts = payload["districts"]

    if len(provinces) != 34:
        print("WARNING: expected 34 provinces, found %d" % len(provinces))

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    province_xml, codes = generate_provinces(provinces)
    (DATA_DIR / "res_country_state_data.xml").write_text(
        province_xml, encoding="utf-8"
    )

    district_xml, district_count, filled = generate_districts(districts, provinces)
    (DATA_DIR / "af_district_data.xml").write_text(district_xml, encoding="utf-8")

    print("provinces: %d (%d distinct ISO codes)" % (len(provinces), len(codes)))
    print("districts: %d" % district_count)
    if filled:
        print(
            "Pashto name taken from Dari for %d district(s): %s"
            % (len(filled), ", ".join(filled))
        )
    print("written to %s" % DATA_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
