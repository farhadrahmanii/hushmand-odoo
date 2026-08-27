# Part of af_hr. See LICENSE file for full copyright and licensing details.
"""Afghan identity and address fields.

These go on ``hr.version`` rather than ``hr.employee`` deliberately. In Odoo 19
an employee record delegates to a version (``_inherits``), and versions form a
dated timeline. Putting the fields here means:

* they read and write from the employee exactly as if they were on it, and
* a corrected name or a change of address becomes **history** rather than
  overwriting what the record said before.

That second point is the reason Odoo 19 replaced contracts with versions, and
it is worth inheriting rather than working around. An earlier plan for this
module included a custom amendment-history model; Odoo now does that natively,
and a parallel history would only have drifted out of step with it.
"""

from odoo import _, api, fields, models


class HrVersion(models.Model):
    _inherit = "hr.version"

    # ------------------------------------------------------------------
    # Naming
    # ------------------------------------------------------------------
    # Afghan names have no inherited surname. A person is identified by their
    # own name plus their father's and grandfather's, and every official
    # document is issued that way, so these are identity fields rather than
    # optional extras.

    af_father_name = fields.Char(
        string="Father's Name",
        groups="hr.group_hr_user",
        tracking=True,
    )
    af_grandfather_name = fields.Char(
        string="Grandfather's Name",
        groups="hr.group_hr_user",
        tracking=True,
    )
    af_full_identity = fields.Char(
        string="Full Identity",
        compute="_compute_af_full_identity",
        groups="hr.group_hr_user",
        help="The name as it is written on official documents and letters.",
    )

    # ------------------------------------------------------------------
    # Tazkira
    # ------------------------------------------------------------------
    # A paper tazkira is identified by three numbers together -- volume,
    # page and registration entry -- not by a single serial. The electronic
    # one has a national identity number instead. Both are in use, so the
    # module records both rather than forcing one into the other's shape.

    af_tazkira_number = fields.Char(
        string="e-Tazkira / NID",
        groups="hr.group_hr_user",
        tracking=True,
        help="National identity number on an electronic tazkira.",
    )
    af_tazkira_volume = fields.Char(
        string="Tazkira Volume",
        groups="hr.group_hr_user",
        tracking=True,
        help="Jild, on a paper tazkira.",
    )
    af_tazkira_page = fields.Char(
        string="Tazkira Page",
        groups="hr.group_hr_user",
        tracking=True,
        help="Safha, on a paper tazkira.",
    )
    af_tazkira_register = fields.Char(
        string="Tazkira Register",
        groups="hr.group_hr_user",
        tracking=True,
        help="Sabt, the registration entry on a paper tazkira.",
    )
    af_tazkira_state_id = fields.Many2one(
        comodel_name="res.country.state",
        string="Tazkira Issued In",
        groups="hr.group_hr_user",
        tracking=True,
        help="The province that issued the tazkira.",
    )
    af_tazkira_reference = fields.Char(
        string="Tazkira Reference",
        compute="_compute_af_tazkira_reference",
        groups="hr.group_hr_user",
        help="Volume, page and register written the way a clerk reads them.",
    )

    af_tin = fields.Char(
        string="TIN",
        groups="hr.group_hr_user",
        tracking=True,
        help="Taxpayer Identification Number, required on the payroll return.",
    )

    # ------------------------------------------------------------------
    # Addresses
    # ------------------------------------------------------------------
    # Odoo's private address stops at the state. Afghan records go two levels
    # further, and distinguish where someone is from (permanent, the address
    # on the tazkira) from where they live now (current).

    af_private_district_id = fields.Many2one(
        comodel_name="af.district",
        string="Current District",
        groups="hr.group_hr_user",
        tracking=True,
    )
    af_private_village_id = fields.Many2one(
        comodel_name="af.village",
        string="Current Village",
        groups="hr.group_hr_user",
        tracking=True,
    )

    af_permanent_state_id = fields.Many2one(
        comodel_name="res.country.state",
        string="Permanent Province",
        groups="hr.group_hr_user",
        tracking=True,
        help="The province recorded on the tazkira.",
    )
    af_permanent_district_id = fields.Many2one(
        comodel_name="af.district",
        string="Permanent District",
        groups="hr.group_hr_user",
        tracking=True,
    )
    af_permanent_village_id = fields.Many2one(
        comodel_name="af.village",
        string="Permanent Village",
        groups="hr.group_hr_user",
        tracking=True,
    )
    af_permanent_street = fields.Char(
        string="Permanent Address",
        groups="hr.group_hr_user",
        tracking=True,
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------

    @api.depends("employee_id.name", "af_father_name", "af_grandfather_name")
    def _compute_af_full_identity(self):
        for version in self:
            parts = [version.employee_id.name or version.name or ""]
            if version.af_father_name:
                parts.append(_("s/o %s") % version.af_father_name)
            if version.af_grandfather_name:
                parts.append(_("g/o %s") % version.af_grandfather_name)
            version.af_full_identity = ", ".join(p for p in parts if p)

    @api.depends("af_tazkira_volume", "af_tazkira_page", "af_tazkira_register")
    def _compute_af_tazkira_reference(self):
        for version in self:
            if not any((version.af_tazkira_volume, version.af_tazkira_page,
                        version.af_tazkira_register)):
                version.af_tazkira_reference = ""
                continue
            version.af_tazkira_reference = _(
                "Volume %(volume)s, Page %(page)s, Register %(register)s"
            ) % {
                "volume": version.af_tazkira_volume or "-",
                "page": version.af_tazkira_page or "-",
                "register": version.af_tazkira_register or "-",
            }

    # ------------------------------------------------------------------
    # Onchanges
    # ------------------------------------------------------------------

    @api.onchange("private_state_id")
    def _onchange_af_private_state(self):
        for version in self:
            if version.af_private_district_id.state_id != version.private_state_id:
                version.af_private_district_id = False

    @api.onchange("af_private_district_id")
    def _onchange_af_private_district(self):
        for version in self:
            if version.af_private_district_id:
                version.private_state_id = version.af_private_district_id.state_id
            if version.af_private_village_id.district_id != version.af_private_district_id:
                version.af_private_village_id = False

    @api.onchange("af_permanent_state_id")
    def _onchange_af_permanent_state(self):
        for version in self:
            if version.af_permanent_district_id.state_id != version.af_permanent_state_id:
                version.af_permanent_district_id = False

    @api.onchange("af_permanent_district_id")
    def _onchange_af_permanent_district(self):
        for version in self:
            if version.af_permanent_district_id:
                version.af_permanent_state_id = version.af_permanent_district_id.state_id
            if version.af_permanent_village_id.district_id != version.af_permanent_district_id:
                version.af_permanent_village_id = False
