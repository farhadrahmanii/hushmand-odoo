# Part of af_l10n_base. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AfDistrict(models.Model):
    _name = "af.district"
    _description = "District"
    _order = "state_id, name"

    name = fields.Char(
        string="Name",
        required=True,
        index=True,
        help="District name in English.",
    )
    name_dr = fields.Char(string="Name (Dari)")
    name_ps = fields.Char(string="Name (Pashto)")
    code = fields.Char(
        string="Code",
        help="Optional local or statistical code for this district.",
    )
    state_id = fields.Many2one(
        comodel_name="res.country.state",
        string="Province",
        required=True,
        ondelete="cascade",
        index=True,
    )
    country_id = fields.Many2one(
        related="state_id.country_id",
        string="Country",
        store=True,
        readonly=True,
    )
    village_ids = fields.One2many(
        comodel_name="af.village",
        inverse_name="district_id",
        string="Villages",
    )
    village_count = fields.Integer(
        compute="_compute_village_count", string="Villages"
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "name_state_uniq",
            "unique(state_id, name)",
            "A district with this name already exists in that province.",
        ),
    ]

    @api.depends("village_ids")
    def _compute_village_count(self):
        # read_group keeps this to one query no matter how many districts are
        # on screen -- the list view shows 546 of them.
        counts = dict(
            self.env["af.village"]._read_group(
                [("district_id", "in", self.ids)],
                groupby=["district_id"],
                aggregates=["__count"],
            )
        )
        for district in self:
            district.village_count = counts.get(district, 0)

    @api.constrains("state_id")
    def _check_state_country(self):
        for district in self:
            if not district.state_id.country_id:
                raise ValidationError(
                    _("The province %s is not linked to a country.")
                    % district.state_id.display_name
                )

    @api.depends_context("lang")
    def _compute_display_name(self):
        """Show the district in the reader's own language where we have it."""
        lang = (self.env.context.get("lang") or "en_US")
        for district in self:
            local = None
            if lang.startswith("ps"):
                local = district.name_ps or district.name_dr
            elif lang.startswith("fa"):
                local = district.name_dr
            district.display_name = local or district.name or ""
