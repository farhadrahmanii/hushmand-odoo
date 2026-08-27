# Part of af_hr. See LICENSE file for full copyright and licensing details.
"""Expose the version fields on the employee record.

``hr.employee`` delegates to ``hr.version``, so plain fields would already be
reachable. Group-restricted ones are the exception: Odoo's own comment in
``hr/models/hr_employee.py`` states that any version field carrying a
``groups`` attribute must also be declared here with ``inherited=True``, or it
is not linked through the delegation properly. Every field below carries a
group, so every one of them needs this.
"""

from odoo import fields, models

_GROUP = "hr.group_hr_user"


def _related(field_type, name, **kwargs):
    """Declare a delegated version field, the way core does it."""
    return field_type(
        readonly=False,
        related="version_id.%s" % name,
        inherited=True,
        groups=_GROUP,
        **kwargs,
    )


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    af_father_name = _related(fields.Char, "af_father_name")
    af_grandfather_name = _related(fields.Char, "af_grandfather_name")
    af_full_identity = fields.Char(
        related="version_id.af_full_identity", inherited=True, groups=_GROUP
    )

    af_tazkira_number = _related(fields.Char, "af_tazkira_number")
    af_tazkira_volume = _related(fields.Char, "af_tazkira_volume")
    af_tazkira_page = _related(fields.Char, "af_tazkira_page")
    af_tazkira_register = _related(fields.Char, "af_tazkira_register")
    af_tazkira_state_id = _related(fields.Many2one, "af_tazkira_state_id")
    af_tazkira_reference = fields.Char(
        related="version_id.af_tazkira_reference", inherited=True, groups=_GROUP
    )
    af_tin = _related(fields.Char, "af_tin")

    af_private_district_id = _related(fields.Many2one, "af_private_district_id")
    af_private_village_id = _related(fields.Many2one, "af_private_village_id")

    af_permanent_state_id = _related(fields.Many2one, "af_permanent_state_id")
    af_permanent_district_id = _related(fields.Many2one, "af_permanent_district_id")
    af_permanent_village_id = _related(fields.Many2one, "af_permanent_village_id")
    af_permanent_street = _related(fields.Char, "af_permanent_street")

    af_discipline_ids = fields.One2many(
        comodel_name="af.employee.discipline",
        inverse_name="employee_id",
        string="Disciplinary Actions",
        groups="hr.group_hr_manager",
    )
    af_discipline_count = fields.Integer(
        compute="_compute_af_discipline_count",
        string="Disciplinary Actions",
        groups="hr.group_hr_manager",
    )

    def _compute_af_discipline_count(self):
        counts = dict(
            self.env["af.employee.discipline"]._read_group(
                [("employee_id", "in", self.ids), ("state", "!=", "cancelled")],
                groupby=["employee_id"],
                aggregates=["__count"],
            )
        )
        for employee in self:
            employee.af_discipline_count = counts.get(employee, 0)

    def action_af_view_disciplines(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Disciplinary Actions",
            "res_model": "af.employee.discipline",
            "view_mode": "list,form",
            "domain": [("employee_id", "=", self.id)],
            "context": {"default_employee_id": self.id},
        }

    def action_af_print_id_card(self):
        return self.env.ref("af_hr.action_report_af_id_card").report_action(self)
