# Part of af_dual_currency. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    af_secondary_currency_id = fields.Many2one(
        related="company_id.af_secondary_currency_id",
        string="Second Currency",
        readonly=True,
    )
    # A view expression cannot walk a dotted path like
    # company_id.af_show_secondary_on_documents, so the flag needs to be a
    # field on this model for the form to test it.
    af_show_secondary = fields.Boolean(
        related="company_id.af_show_secondary_on_documents",
        string="Show Second Currency",
        readonly=True,
    )
    af_exchange_period_id = fields.Many2one(
        comodel_name="af.exchange.period",
        string="Exchange Period",
        compute="_compute_af_secondary_amount",
        store=True,
        help="The period whose rate was used for the second-currency total.",
    )
    af_amount_total_secondary = fields.Monetary(
        string="Total in Second Currency",
        currency_field="af_secondary_currency_id",
        compute="_compute_af_secondary_amount",
        store=True,
        help="The document total converted at the rate agreed for its period. "
             "Zero means no confirmed period covers this date.",
    )

    @api.depends(
        "amount_total",
        "invoice_date",
        "date",
        "company_id.af_secondary_currency_id",
        "currency_id",
    )
    def _compute_af_secondary_amount(self):
        period_model = self.env["af.exchange.period"]
        for move in self:
            secondary = move.company_id.af_secondary_currency_id
            if not secondary or secondary == move.company_currency_id:
                move.af_amount_total_secondary = 0.0
                move.af_exchange_period_id = False
                continue

            # A draft bill has no invoice_date yet; fall back to the
            # accounting date so the figure is not blank while it is edited.
            reference_date = move.invoice_date or move.date

            # amount_total is in the document currency, which is not always
            # the company currency. Convert to company currency first, then
            # apply the agreed period rate -- doing it in one step would use
            # Odoo's daily rate and quietly bypass the whole point of periods.
            base = move.amount_total
            if move.currency_id and move.currency_id != move.company_currency_id:
                base = move.currency_id._convert(
                    move.amount_total,
                    move.company_currency_id,
                    move.company_id,
                    reference_date or fields.Date.context_today(move),
                )

            amount, period = period_model._convert(
                base, reference_date, company=move.company_id, currency=secondary
            )
            move.af_amount_total_secondary = amount
            move.af_exchange_period_id = period
