# Part of af_liaison. See LICENSE file for full copyright and licensing details.
"""Afghan official documents.

This module is deliberately thin. The tracking, reminders and renewal chain
all live in hm_expiry_docs, because a visa and a vehicle registration are the
same shape. What is Afghanistan-specific is which documents matter, who holds
them, and the fact that a liaison officer -- not the holder -- is usually the
person who has to get them renewed.
"""

from odoo import _, api, fields, models


class HmExpiryDocument(models.Model):
    _inherit = "hm.expiry.document"

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Employee",
        index="btree_not_null",
        tracking=True,
        help="The staff member this document belongs to.",
    )
    af_province_id = fields.Many2one(
        comodel_name="res.country.state",
        string="Issued In",
        tracking=True,
        help="The province that issued the document.",
    )
    af_reference = fields.Char(
        string="Official Reference",
        help="The maktoob or file reference the issuing office quotes.",
    )

    @api.onchange("employee_id")
    def _onchange_employee_fills_holder(self):
        """A document for an employee is held by that employee."""
        for document in self:
            if not document.employee_id:
                continue
            if not document.subject:
                document.subject = document.employee_id.name
            if not document.partner_id and document.employee_id.work_contact_id:
                document.partner_id = document.employee_id.work_contact_id

    @api.depends("employee_id")
    def _compute_display_name(self):
        super()._compute_display_name()
        for document in self:
            if document.employee_id and not document.partner_id:
                document.display_name = "%s - %s" % (
                    document.display_name.split(" - ")[0],
                    document.employee_id.name,
                )


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    af_document_ids = fields.One2many(
        comodel_name="hm.expiry.document",
        inverse_name="employee_id",
        string="Official Documents",
        groups="hr.group_hr_user",
    )
    af_document_count = fields.Integer(
        compute="_compute_af_document_count",
        string="Documents",
        groups="hr.group_hr_user",
    )
    af_document_alert = fields.Boolean(
        compute="_compute_af_document_count",
        string="Document Needs Attention",
        groups="hr.group_hr_user",
        help="At least one document is expiring or has expired.",
    )

    def _compute_af_document_count(self):
        Document = self.env["hm.expiry.document"]
        totals = dict(Document._read_group(
            [("employee_id", "in", self.ids)],
            groupby=["employee_id"], aggregates=["__count"],
        ))
        alerting = dict(Document._read_group(
            [("employee_id", "in", self.ids),
             ("state", "in", ("expiring", "expired"))],
            groupby=["employee_id"], aggregates=["__count"],
        ))
        for employee in self:
            employee.af_document_count = totals.get(employee, 0)
            employee.af_document_alert = bool(alerting.get(employee, 0))

    def action_af_view_documents(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Official Documents"),
            "res_model": "hm.expiry.document",
            "view_mode": "list,form",
            "domain": [("employee_id", "=", self.id)],
            "context": {
                "default_employee_id": self.id,
                "default_subject": self.name,
            },
        }
