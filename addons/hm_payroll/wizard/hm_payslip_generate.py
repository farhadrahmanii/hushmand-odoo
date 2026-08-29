# Part of hm_payroll. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import UserError


class HmPayslipGenerate(models.TransientModel):
    _name = "hm.payslip.generate"
    _description = "Generate Payslips"

    run_id = fields.Many2one(
        comodel_name="hm.payslip.run",
        string="Batch",
        required=True,
    )
    company_id = fields.Many2one(
        related="run_id.company_id", readonly=True,
    )
    employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        string="Employees",
        domain="['|', ('company_id', '=', False),"
               " ('company_id', '=', company_id)]",
    )

    def action_generate(self):
        """One draft payslip per employee, computed immediately.

        An employee who already has a payslip in the batch is skipped, so
        running the wizard twice cannot pay anyone twice.
        """
        self.ensure_one()
        run = self.run_id
        if run.state != "draft":
            raise UserError(_("%s is closed.") % run.name)
        if not self.employee_ids:
            raise UserError(_("Choose at least one employee."))

        employees = self.employee_ids - run.slip_ids.mapped("employee_id")
        slips = self.env["hm.payslip"]
        for employee in employees:
            slips |= self.env["hm.payslip"].create({
                "employee_id": employee.id,
                "structure_id": run.structure_id.id,
                "date_from": run.date_from,
                "date_to": run.date_to,
                "company_id": run.company_id.id,
                "run_id": run.id,
            })
        slips.action_compute_sheet()
        return {"type": "ir.actions.act_window_close"}
