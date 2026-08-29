# Part of af_hr_payroll. See LICENSE file for full copyright and licensing details.
"""Wiring the Afghan tax scale into the payroll engine.

A salary rule is a text field a payroll manager edits. Asking that manager to
paste a four-bracket progressive formula into it is how tax gets computed
wrongly, so the rule is handed a function instead:

    result = -af_income_tax(categories['GROSS'])

Everything difficult -- which scale is in force for this period, converting a
dollar salary into afghani because that is what the tax is assessed in, and
back again -- happens on this side of that call.
"""

from odoo import _, models
from odoo.exceptions import UserError


class HmPayslip(models.Model):
    _inherit = "hm.payslip"

    # ------------------------------------------------------------------
    # Currency
    # ------------------------------------------------------------------

    def _af_tax_rate_to(self, scale):
        """Rate converting one unit of payslip currency into scale currency.

        Returns 1.0 when no conversion is needed. Raises rather than guessing:
        a payslip is a legal document and a silently wrong tax figure is worse
        than a refusal to compute one.
        """
        self.ensure_one()
        if scale.currency_id == self.currency_id:
            return 1.0

        Period = self.env["af.exchange.period"]
        amount, period = Period._convert(
            1.0, self.date_to, company=self.company_id,
            currency=scale.currency_id,
        )
        if not period:
            raise UserError(
                _("This payslip is in %(slip)s but Afghan income tax is "
                  "assessed in %(scale)s, and no confirmed exchange period "
                  "covers %(date)s.\n\n"
                  "Confirm the exchange period for that month, then compute "
                  "the payslip again.")
                % {"slip": self.currency_id.name,
                   "scale": scale.currency_id.name,
                   "date": self.date_to}
            )
        return amount

    # ------------------------------------------------------------------
    # The helper rules call
    # ------------------------------------------------------------------

    def _af_periods_per_year(self):
        """How many pay periods a year this payslip represents.

        The Afghan scale is monthly. A fortnightly slip has to be annualised
        before the brackets are read, or half a month's pay looks like a poor
        salary and is taxed in a band the same annual wage would never reach.
        """
        self.ensure_one()
        if not (self.date_from and self.date_to):
            return 12.0
        days = (self.date_to - self.date_from).days + 1
        # Rounded to the nearest sensible frequency rather than used raw:
        # a 28-day and a 31-day month are both a month, and dividing by an
        # exact day count would tax February differently from January.
        if days <= 10:
            return 52.0
        if days <= 20:
            return 26.0
        if days <= 45:
            return 12.0
        if days <= 135:
            return 4.0
        return 1.0

    def _af_income_tax(self, taxable):
        """Afghan wage withholding tax on ``taxable``, in payslip currency.

        Positive. A deduction rule negates it.
        """
        self.ensure_one()
        if not taxable or taxable <= 0:
            return 0.0

        scale = self.env["af.income.tax.scale"]._scale_for(
            self.date_from or self.date_to, company=self.company_id
        )
        if not scale:
            raise UserError(
                _("No income tax scale is in force for %(date)s.\n\n"
                  "Payroll cannot compute tax without one. Open Payroll > "
                  "Configuration > Income Tax Scales and set the period the "
                  "scale covers.")
                % {"date": self.date_from or self.date_to}
            )

        rate = self._af_tax_rate_to(scale)
        tax_in_scale_currency = scale.compute_tax(
            taxable * rate, periods_per_year=self._af_periods_per_year()
        )
        return self.currency_id.round(tax_in_scale_currency / rate)

    def _rule_eval_context(self, categories, inputs):
        context = super()._rule_eval_context(categories, inputs)
        context["af_income_tax"] = self._af_income_tax
        return context
