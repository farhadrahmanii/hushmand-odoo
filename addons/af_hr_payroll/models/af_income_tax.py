# Part of af_hr_payroll. See LICENSE file for full copyright and licensing details.
"""Afghan wage withholding tax.

Afghanistan taxes salaries on a monthly progressive scale. An employer
withholds the tax from each salary and remits it, so the figure has to be on
the payslip and it has to be right.

The scale is data, not code, and it is effective-dated. Tax law changes; a
rate compiled into a Python file means every customer waits for a new release
and every historical payslip silently recomputes on the new rate when it is
reopened. A dated table means a payslip for last year is still taxed the way
last year was taxed.
"""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AfIncomeTaxScale(models.Model):
    _name = "af.income.tax.scale"
    _description = "Income Tax Scale"
    _order = "date_from desc, id desc"

    name = fields.Char(required=True)
    date_from = fields.Date(
        required=True,
        help="The scale applies to payslips whose period starts on or after "
             "this date.",
    )
    date_to = fields.Date(
        help="Leave empty while the scale is the current one.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        required=True,
        help="The currency the brackets are stated in. Afghan tax is assessed "
             "in afghani, so a salary paid in dollars is converted before the "
             "scale is applied.",
    )
    bracket_ids = fields.One2many(
        comodel_name="af.income.tax.bracket",
        inverse_name="scale_id",
        string="Brackets",
    )
    active = fields.Boolean(default=True)
    note = fields.Text(string="Notes")

    _period_order = models.Constraint(
        "CHECK(date_to IS NULL OR date_to >= date_from)",
        "A scale cannot end before it starts.",
    )

    @api.constrains("bracket_ids")
    def _check_brackets_are_a_scale(self):
        """A scale with a hole or an overlap taxes some salary twice and some
        not at all, and neither shows up until somebody checks a payslip by
        hand."""
        for scale in self:
            brackets = scale.bracket_ids.sorted("amount_from")
            if not brackets:
                continue
            if brackets[0].amount_from != 0:
                raise ValidationError(
                    _("The lowest bracket of %s has to start at zero, or "
                      "salaries below it would not be taxed at all.")
                    % scale.name
                )
            for lower, upper in zip(brackets, brackets[1:]):
                if not lower.amount_to:
                    raise ValidationError(
                        _("Only the highest bracket of %s may be open-ended.")
                        % scale.name
                    )
                if upper.amount_from != lower.amount_to:
                    raise ValidationError(
                        _("The brackets of %(scale)s leave a gap or overlap "
                          "between %(lower)s and %(upper)s. Each bracket has "
                          "to start exactly where the one below it ends.")
                        % {"scale": scale.name,
                           "lower": lower.amount_to,
                           "upper": upper.amount_from}
                    )
            if brackets[-1].amount_to:
                raise ValidationError(
                    _("The highest bracket of %s has to be open-ended, or a "
                      "large enough salary would fall off the top of the "
                      "scale untaxed.") % scale.name
                )

    @api.model
    def _scale_for(self, date, company=None):
        """The scale in force on a date. Returns an empty recordset if none."""
        company = company or self.env.company
        return self.search(
            [
                ("company_id", "=", company.id),
                ("date_from", "<=", date),
                "|", ("date_to", "=", False), ("date_to", ">=", date),
            ],
            order="date_from desc",
            limit=1,
        )

    def compute_tax(self, taxable, periods_per_year=12.0):
        """Tax on ``taxable``, which is one period's pay in this scale's
        currency.

        The Afghan scale is stated per month. A payslip covering something
        other than a month -- a fortnight, or a half-month starter -- has to
        be annualised before the brackets are read, or a fortnightly salary
        looks poor enough to fall into a lower band than the same annual
        wage earns monthly.
        """
        self.ensure_one()
        if taxable <= 0:
            return 0.0

        monthly = taxable * periods_per_year / 12.0
        tax_monthly = 0.0
        for bracket in self.bracket_ids.sorted("amount_from"):
            if monthly <= bracket.amount_from:
                continue
            if bracket.amount_to and monthly > bracket.amount_to:
                continue
            tax_monthly = (
                bracket.base_amount
                + (monthly - bracket.amount_from) * bracket.rate / 100.0
            )
            break

        return tax_monthly * 12.0 / periods_per_year


class AfIncomeTaxBracket(models.Model):
    _name = "af.income.tax.bracket"
    _description = "Income Tax Bracket"
    _order = "amount_from, id"

    scale_id = fields.Many2one(
        comodel_name="af.income.tax.scale",
        required=True,
        ondelete="cascade",
        index=True,
    )
    currency_id = fields.Many2one(
        related="scale_id.currency_id", readonly=True,
    )
    amount_from = fields.Monetary(string="From", required=True)
    amount_to = fields.Monetary(
        string="To",
        help="Leave at zero for the highest bracket, which has no ceiling.",
    )
    base_amount = fields.Monetary(
        string="Fixed Amount",
        help="Tax on everything below this bracket, carried forward so the "
             "rate only applies to the part of the salary inside it.",
    )
    rate = fields.Float(
        string="Rate (%)",
        digits=(5, 2),
        help="Applied to the part of the salary above the bracket floor, not "
             "to the whole salary.",
    )

    _rate_is_a_percentage = models.Constraint(
        "CHECK(rate >= 0 AND rate <= 100)",
        "A tax rate has to be between 0 and 100 percent.",
    )
    _bracket_order = models.Constraint(
        "CHECK(amount_to = 0 OR amount_to > amount_from)",
        "A bracket has to end above where it starts.",
    )

    @api.depends("amount_from", "amount_to", "rate")
    def _compute_display_name(self):
        for bracket in self:
            if bracket.amount_to:
                span = "%s - %s" % (bracket.amount_from, bracket.amount_to)
            else:
                span = "%s and above" % bracket.amount_from
            bracket.display_name = "%s @ %s%%" % (span, bracket.rate)
