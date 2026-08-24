# Part of af_l10n_base. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    af_district_id = fields.Many2one(
        comodel_name="af.district",
        string="District",
        index=True,
        help="District within the selected province.",
    )
    af_village_id = fields.Many2one(
        comodel_name="af.village",
        string="Village",
        index=True,
    )
    af_tazkira = fields.Char(
        string="Tazkira Number",
        help="Afghan national identity document number.",
    )
    af_tin = fields.Char(
        string="TIN",
        help="Taxpayer Identification Number issued by the Afghanistan "
             "Revenue Department.",
    )

    # Odoo builds a printed address by substituting field names into the
    # country's address_format, and validates that format against
    # _formatting_address_fields(). A key it does not know about is rejected
    # outright, so the district and village have to be registered there as
    # plain text fields -- the same approach Odoo's own base_address_extended
    # takes for street_name and street_number.
    af_district_name = fields.Char(
        related="af_district_id.name",
        string="District Name",
        readonly=True,
    )
    af_village_name = fields.Char(
        related="af_village_id.name",
        string="Village Name",
        readonly=True,
    )

    @api.model
    def _formatting_address_fields(self):
        """Allow %(af_district_name)s and %(af_village_name)s in a layout.

        Only _formatting_address_fields is extended, not _address_fields:
        these are for display, and must not join the set of fields Odoo
        synchronises from a parent contact down to its children.
        """
        return super()._formatting_address_fields() + [
            "af_district_name",
            "af_village_name",
        ]

    @api.onchange("state_id")
    def _onchange_state_clears_district(self):
        """A district from another province would be nonsense; drop it."""
        for partner in self:
            if partner.af_district_id.state_id != partner.state_id:
                partner.af_district_id = False

    @api.onchange("af_district_id")
    def _onchange_district(self):
        """Filling the district fills the province, and clears a stale village."""
        for partner in self:
            if partner.af_district_id:
                partner.state_id = partner.af_district_id.state_id
                partner.country_id = partner.af_district_id.country_id
            if partner.af_village_id.district_id != partner.af_district_id:
                partner.af_village_id = False

    @api.onchange("af_village_id")
    def _onchange_village(self):
        for partner in self:
            if partner.af_village_id:
                partner.af_district_id = partner.af_village_id.district_id

