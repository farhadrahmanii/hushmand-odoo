# Part of af_l10n_base. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests import common, tagged
from psycopg2 import IntegrityError
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestAfGeographyData(common.TransactionCase):
    """The data itself. If a customer opens the province list and finds 33
    entries or a district in the wrong province, the module has failed at the
    only thing it exists to do."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.afghanistan = cls.env.ref("base.af")
        cls.states = cls.env["res.country.state"].search(
            [("country_id", "=", cls.afghanistan.id)]
        )

    def test_all_34_provinces_loaded(self):
        self.assertEqual(len(self.states), 34)

    def test_provinces_have_iso_codes(self):
        """Codes are the published ISO 3166-2:AF ones, which is what makes the
        data interoperable with anything else."""
        codes = set(self.states.mapped("code"))
        self.assertEqual(len(codes), 34, "province codes are not unique")
        for expected in ("KAB", "KAN", "HER", "BAL", "NAN", "BDS", "NIM"):
            self.assertIn(expected, codes)

    def test_provinces_are_trilingual(self):
        missing_dari = self.states.filtered(lambda s: not s.af_name_dr)
        self.assertFalse(
            missing_dari,
            "provinces without a Dari name: %s" % missing_dari.mapped("name"),
        )
        missing_pashto = self.states.filtered(lambda s: not s.af_name_ps)
        self.assertFalse(missing_pashto)

    def test_district_count(self):
        districts = self.env["af.district"].search(
            [("country_id", "=", self.afghanistan.id)]
        )
        self.assertEqual(len(districts), 546)

    def test_every_district_has_a_province(self):
        orphans = self.env["af.district"].search([("state_id", "=", False)])
        self.assertFalse(orphans)

    def test_districts_are_trilingual(self):
        """Delaram had no Pashto name in the source database; the generator
        falls back to Dari and reports it, so nothing ships blank."""
        untranslated = self.env["af.district"].search(
            ["|", ("name_dr", "in", [False, ""]),
                  ("name_ps", "in", [False, ""])]
        )
        self.assertFalse(
            untranslated,
            "districts missing a translation: %s"
            % untranslated[:5].mapped("name"),
        )

    def test_kabul_has_its_districts(self):
        kabul = self.env.ref("af_l10n_base.state_af_kab")
        districts = self.env["af.district"].search([("state_id", "=", kabul.id)])
        self.assertGreater(len(districts), 10)
        self.assertIn("Bagrami", districts.mapped("name"))

    def test_names_are_not_shouting(self):
        """The source database stores KABUL; an invoice should read Kabul."""
        self.assertEqual(self.env.ref("af_l10n_base.state_af_kab").name, "Kabul")
        self.assertEqual(
            self.env.ref("af_l10n_base.state_af_sar").name, "Sar-e Pol"
        )

    def test_villages_ship_empty(self):
        """Deliberate: no trustworthy dataset exists, so none is invented."""
        self.assertEqual(self.env["af.village"].search_count([]), 0)


@tagged("post_install", "-at_install")
class TestLanguageAwareNames(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Odoo refuses an inactive language in the context, so switch on the
        # two this module creates.
        cls.env["res.lang"]._activate_lang("fa_AF")
        cls.env["res.lang"]._activate_lang("ps_AF")
        cls.kabul_province = cls.env.ref("af_l10n_base.state_af_kab")
        cls.district = cls.env["af.district"].search(
            [("state_id", "=", cls.kabul_province.id)], limit=1
        )

    def test_province_english_by_default(self):
        # Core renders a state as "Kabul (AF)" in some contexts, so assert on
        # the name rather than pinning core's exact wrapper.
        display = self.kabul_province.with_context(lang="en_US").display_name
        self.assertIn("Kabul", display)

    def test_province_in_dari(self):
        display = self.kabul_province.with_context(lang="fa_AF").display_name
        self.assertIn(self.kabul_province.af_name_dr, display)
        self.assertNotIn("Kabul", display)

    def test_province_in_pashto(self):
        display = self.kabul_province.with_context(lang="ps_AF").display_name
        self.assertIn(self.kabul_province.af_name_ps, display)

    def test_other_countries_are_untouched(self):
        """Only Afghan states change; every other country keeps Odoo's own
        display, including the '(COUNTRY)' suffix used in some contexts."""
        france = self.env.ref("base.fr")
        other = self.env["res.country.state"].search(
            [("country_id", "!=", self.env.ref("base.af").id)], limit=1
        )
        if other:
            english = other.with_context(lang="en_US").display_name
            dari = other.with_context(lang="fa_AF").display_name
            self.assertEqual(english, dari)
        self.assertTrue(france)

    def test_district_in_dari(self):
        self.assertEqual(
            self.district.with_context(lang="fa_AF").display_name,
            self.district.name_dr,
        )

    def test_district_in_pashto(self):
        self.assertEqual(
            self.district.with_context(lang="ps_AF").display_name,
            self.district.name_ps,
        )

    def test_district_english_by_default(self):
        self.assertEqual(
            self.district.with_context(lang="en_US").display_name,
            self.district.name,
        )


@tagged("post_install", "-at_install")
class TestDistrictModel(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.province = cls.env.ref("af_l10n_base.state_af_kab")

    @mute_logger("odoo.sql_db")
    def test_duplicate_district_rejected(self):
        self.env["af.district"].create(
            {"name": "Testville", "state_id": self.province.id}
        )
        with self.assertRaises(IntegrityError):
            with self.cr.savepoint():
                self.env["af.district"].create(
                    {"name": "Testville", "state_id": self.province.id}
                )

    def test_same_name_in_another_province_is_fine(self):
        other = self.env.ref("af_l10n_base.state_af_her")
        self.env["af.district"].create(
            {"name": "Sharedname", "state_id": self.province.id}
        )
        self.env["af.district"].create(
            {"name": "Sharedname", "state_id": other.id}
        )

    def test_village_count(self):
        district = self.env["af.district"].create(
            {"name": "Counted", "state_id": self.province.id}
        )
        self.assertEqual(district.village_count, 0)
        self.env["af.village"].create(
            {"name": "One", "district_id": district.id}
        )
        self.env["af.village"].create(
            {"name": "Two", "district_id": district.id}
        )
        district.invalidate_recordset(["village_count"])
        self.assertEqual(district.village_count, 2)

    def test_village_inherits_province(self):
        district = self.env["af.district"].create(
            {"name": "Parented", "state_id": self.province.id}
        )
        village = self.env["af.village"].create(
            {"name": "Child", "district_id": district.id}
        )
        self.assertEqual(village.state_id, self.province)
        self.assertEqual(village.country_id, self.env.ref("base.af"))


@tagged("post_install", "-at_install")
class TestPartnerAddress(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.afghanistan = cls.env.ref("base.af")
        cls.province = cls.env.ref("af_l10n_base.state_af_kab")
        cls.district = cls.env["af.district"].search(
            [("state_id", "=", cls.province.id)], limit=1
        )

    def test_partner_accepts_district(self):
        partner = self.env["res.partner"].create({
            "name": "Test Contact",
            "country_id": self.afghanistan.id,
            "state_id": self.province.id,
            "af_district_id": self.district.id,
            "af_tazkira": "1401-1234-56789",
            "af_tin": "9001234567",
        })
        self.assertEqual(partner.af_district_id, self.district)
        self.assertEqual(partner.af_tin, "9001234567")

    def test_choosing_a_district_fills_the_province(self):
        partner = self.env["res.partner"].new({"name": "Onchange Test"})
        partner.af_district_id = self.district
        partner._onchange_district()
        self.assertEqual(partner.state_id, self.province)
        self.assertEqual(partner.country_id, self.afghanistan)

    def test_changing_province_clears_a_foreign_district(self):
        partner = self.env["res.partner"].new({
            "name": "Onchange Test",
            "state_id": self.province.id,
            "af_district_id": self.district.id,
        })
        partner.state_id = self.env.ref("af_l10n_base.state_af_her")
        partner._onchange_state_clears_district()
        self.assertFalse(partner.af_district_id)

    def test_district_appears_in_printed_address(self):
        partner = self.env["res.partner"].create({
            "name": "Printed Address",
            "street": "Street 1",
            "city": "Kabul",
            "country_id": self.afghanistan.id,
            "state_id": self.province.id,
            "af_district_id": self.district.id,
        })
        self.assertIn(self.district.name, partner.contact_address)

    def test_address_format_registered_for_afghanistan(self):
        self.assertIn("af_district_name", self.afghanistan.address_format)

    def test_custom_keys_are_legal_format_keys(self):
        """Odoo validates address_format against _formatting_address_fields,
        and rejects any key it does not know. This is what that failure looked
        like the first time: KeyError, then 'invalid format key'."""
        allowed = self.env["res.partner"]._formatting_address_fields()
        self.assertIn("af_district_name", allowed)
        self.assertIn("af_village_name", allowed)

    def test_parent_child_sync_is_not_affected(self):
        """Only the formatting list is extended, never the sync list."""
        self.assertNotIn(
            "af_district_name", self.env["res.partner"]._address_fields()
        )


@tagged("post_install", "-at_install")
class TestLanguages(common.TransactionCase):
    """Odoo ships Persian and nothing else from the region. Without these two
    records a customer cannot select Dari or Pashto at all, which would make
    the module's trilingual data pointless."""

    def test_dari_language_exists(self):
        dari = self.env.ref("af_l10n_base.lang_fa_af")
        self.assertEqual(dari.code, "fa_AF")
        self.assertEqual(dari.direction, "rtl")

    def test_pashto_language_exists(self):
        pashto = self.env.ref("af_l10n_base.lang_ps_af")
        self.assertEqual(pashto.code, "ps_AF")
        self.assertEqual(pashto.direction, "rtl")

    def test_week_starts_on_saturday(self):
        for xml_id in ("af_l10n_base.lang_fa_af", "af_l10n_base.lang_ps_af"):
            with self.subTest(xml_id):
                self.assertEqual(self.env.ref(xml_id).week_start, "6")

    def test_languages_can_be_activated(self):
        self.env["res.lang"]._activate_lang("fa_AF")
        self.assertTrue(self.env.ref("af_l10n_base.lang_fa_af").active)
