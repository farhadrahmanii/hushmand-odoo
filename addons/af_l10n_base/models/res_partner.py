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

    def _prepare_display_address(self, without_company=False):
        """Make the district available to address formats as %(district_name)s.

        Odoo builds printed addresses from a per-country format string. Adding
        the value here is the supported way to expose an extra field to it.
        """
        address_format, args = super()._prepare_display_address(without_company)
        args["district_name"] = self.af_district_id.name or ""
        args["village_name"] = self.af_village_id.name or ""
        return address_format, args
