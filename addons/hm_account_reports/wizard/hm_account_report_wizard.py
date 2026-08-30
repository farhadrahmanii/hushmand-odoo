# Part of hm_account_reports. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


def _year_start():
    today = fields.Date.today()
    return today.replace(month=1, day=1)


class HmAccountReportWizard(models.TransientModel):
    _name = "hm.account.report.wizard"
    _description = "Financial Report"
    _inherit = ["hm.license.gate"]
    _licence_module = "hm_account_reports"

    report_type = fields.Selection(
        selection=[
            ("trial_balance", "Trial Balance"),
            ("profit_and_loss", "Profit and Loss"),
            ("balance_sheet", "Balance Sheet"),
        ],
        string="Report",
        required=True,
        default="trial_balance",
    )
    company_ids = fields.Many2many(
        comodel_name="res.company",
        string="Companies",
        required=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date(
        string="From", required=True, default=lambda self: _year_start(),
    )
    date_to = fields.Date(
        string="To", required=True, default=fields.Date.context_today,
    )
    posted_only = fields.Boolean(
        string="Posted Entries Only",
        default=True,
        help="Leave this on for anything you intend to file. Draft entries "
             "are not part of the books yet.",
    )
    hide_zero = fields.Boolean(
        string="Hide Empty Accounts",
        default=True,
    )
    journal_ids = fields.Many2many(
        comodel_name="account.journal",
        string="Journals",
        help="Leave empty for all journals.",
    )
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Budget Line",
        help="Restrict to entries carrying this analytic account.",
    )

    @api.onchange("report_type")
    def _onchange_report_type(self):
        """A balance sheet is a position at a date, not a period."""
        for wizard in self:
            if wizard.report_type == "balance_sheet" and not wizard.date_to:
                wizard.date_to = fields.Date.context_today(wizard)

    def _options(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_("The start date is after the end date."))
        return {
            "report_type": self.report_type,
            "company_ids": self.company_ids.ids,
            "date_from": self.date_from,
            # The day before the period starts, for opening balances.
            "date_from_before": self.date_from - relativedelta(days=1),
            "date_to": self.date_to,
            "posted_only": self.posted_only,
            "hide_zero": self.hide_zero,
            "journal_ids": self.journal_ids.ids,
            "analytic_account_id": self.analytic_account_id.id or False,
        }

    def _report_data(self):
        """Everything a template needs to render."""
        self.ensure_one()
        options = self._options()
        engine = self.env["hm.account.report"]
        data = getattr(engine, self.report_type)(options)
        data.update({
            "options": options,
            "report_type": self.report_type,
            "report_name": dict(
                self._fields["report_type"].selection
            )[self.report_type],
            "company_names": ", ".join(self.company_ids.mapped("name")),
            "currency": self.env.company.currency_id,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "posted_only": self.posted_only,
        })
        return data

    def action_print(self):
        self.ensure_one()
        return self.env.ref("hm_account_reports.action_report_financial").report_action(
            self, data={"wizard_id": self.id}
        )
