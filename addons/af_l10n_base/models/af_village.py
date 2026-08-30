# Part of af_l10n_base. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AfVillage(models.Model):
    """Villages, the level below a district.

    This model ships **empty**. The Hushmand ERP villages table was never
    populated, and no reliable public dataset of Afghan villages exists, so
    seeding it would mean inventing data. The structure is here so that
    organisations working at village level can enter their own, and so that
    modules built on top of this one can rely on the model existing.
    """

    _name = "af.village"
    _description = "Village"
    _inherit = ["hm.license.gate"]
    _licence_module = "af_l10n_base"
    _order = "district_id, name"

    name = fields.Char(string="Name", required=True, index=True)
    name_dr = fields.Char(string="Name (Dari)")
    name_ps = fields.Char(string="Name (Pashto)")
    code = fields.Char(
        string="Code",
        help="Optional village code, for example from a census or survey.",
    )
    district_id = fields.Many2one(
        comodel_name="af.district",
        string="District",
        required=True,
        ondelete="cascade",
        index=True,
    )
    state_id = fields.Many2one(
        related="district_id.state_id",
        string="Province",
        store=True,
        readonly=True,
        index=True,
    )
    country_id = fields.Many2one(
        related="district_id.country_id",
        string="Country",
        store=True,
        readonly=True,
    )
    active = fields.Boolean(default=True)

    _name_district_uniq = models.Constraint(
        "unique(district_id, name)",
        "A village with this name already exists in that district.",
    )

    @api.depends("name", "name_dr", "name_ps")
    @api.depends_context("lang")
    def _compute_display_name(self):
        lang = self.env.context.get("lang") or "en_US"
        for village in self:
            local = None
            if lang.startswith("ps"):
                local = village.name_ps or village.name_dr
            elif lang.startswith("fa"):
                local = village.name_dr
            village.display_name = local or village.name or ""
