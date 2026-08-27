# Part of af_dual_currency. See LICENSE file for full copyright and licensing details.
"""Exchange rate periods.

Odoo stores one rate per date and picks the nearest one when converting. That
works for a business that marks to market daily. It does not fit an Afghan
organisation, which fixes a single rate for a whole month and uses it for
payroll, tax filings and every document issued in that month.

Two things are missing from the plain rate table:

* nothing groups a month's documents to one agreed rate, and
* nothing stops someone editing a historical rate, which silently changes
  figures that have already been reported to the ministry.

A period supplies both. On confirmation it writes an ordinary
``res.currency.rate``, so the rest of Odoo -- invoices, accounting, reports --
keeps working exactly as it always did. The period adds governance on top
rather than replacing the mechanism.
"""

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AfExchangePeriod(models.Model):
    _name = "af.exchange.period"
    _description = "Exchange Rate Period"
    _order = "date_from desc, id desc"
    _rec_name = "display_name"

    name = fields.Char(
        string="Reference",
        required=True,
        help="A label for the period, for example 2026-08 or Sunbula 1405.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    company_currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="Company Currency",
        readonly=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Second Currency",
        required=True,
        default=lambda self: self.env.company.af_secondary_currency_id,
        domain="[('id', '!=', company_currency_id)]",
        help="The currency this period sets a rate for, normally AFN.",
    )
    date_from = fields.Date(string="From", required=True, index=True)
    date_to = fields.Date(string="To", required=True, index=True)
    rate = fields.Float(
        string="Rate",
        digits=(16, 6),
        required=True,
        help="Units of the second currency for one unit of the company "
             "currency. With a company in USD and a rate of 70, one dollar "
             "is 70 afghani.",
    )
    inverse_rate = fields.Float(
        string="Inverse Rate",
        digits=(16, 6),
        compute="_compute_inverse_rate",
        help="The same rate read the other way round, for checking.",
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("closed", "Closed"),
        ],
        default="draft",
        required=True,
        index=True,
        help="Draft periods can still be edited. Confirming publishes the "
             "rate to Odoo. Closing locks it so reported figures cannot "
             "change afterwards.",
    )
    rate_id = fields.Many2one(
        comodel_name="res.currency.rate",
        string="Published Rate",
        readonly=True,
        ondelete="set null",
        help="The Odoo currency rate created when this period was confirmed.",
    )
    note = fields.Text(
        string="Notes",
        help="Where the rate came from, for example the central bank "
             "reference for a given day.",
    )

    _date_order = models.Constraint(
        "CHECK (date_from <= date_to)",
        "A period cannot end before it starts.",
    )
    _rate_positive = models.Constraint(
        "CHECK (rate > 0)",
        "The rate must be greater than zero.",
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------

    @api.depends("name", "currency_id", "rate")
    def _compute_display_name(self):
        for period in self:
            if period.currency_id and period.rate:
                period.display_name = "%s (%s %s)" % (
                    period.name or "",
                    period.currency_id.name,
                    period.rate,
                )
            else:
                period.display_name = period.name or ""

    @api.depends("rate")
    def _compute_inverse_rate(self):
        for period in self:
            period.inverse_rate = (1.0 / period.rate) if period.rate else 0.0

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------

    @api.constrains("date_from", "date_to", "currency_id", "company_id")
    def _check_no_overlap(self):
        """Two periods covering the same day would make the rate ambiguous."""
        for period in self:
            overlapping = self.search([
                ("id", "!=", period.id),
                ("company_id", "=", period.company_id.id),
                ("currency_id", "=", period.currency_id.id),
                ("date_from", "<=", period.date_to),
                ("date_to", ">=", period.date_from),
            ], limit=1)
            if overlapping:
                raise ValidationError(
                    _("This period overlaps with %(other)s, which already "
                      "covers %(start)s to %(end)s.")
                    % {
                        "other": overlapping.name,
                        "start": overlapping.date_from,
                        "end": overlapping.date_to,
                    }
                )

    @api.constrains("currency_id", "company_id")
    def _check_currency_differs(self):
        for period in self:
            if period.currency_id == period.company_id.currency_id:
                raise ValidationError(
                    _("The second currency must differ from the company "
                      "currency (%s).") % period.company_id.currency_id.name
                )

    # ------------------------------------------------------------------
    # Guards
    # ------------------------------------------------------------------

    LOCKED_FIELDS = ("rate", "date_from", "date_to", "currency_id", "company_id")

    def write(self, vals):
        """A closed period is history; it must not be rewritten.

        This is the point of the model. Editing a rate after the month has
        been reported changes figures that have already left the building.
        """
        if any(field in vals for field in self.LOCKED_FIELDS):
            closed = self.filtered(lambda p: p.state == "closed")
            if closed:
                raise UserError(
                    _("%s is closed. Reopen it before changing the rate, and "
                      "be aware that anything already reported using it will "
                      "no longer match.") % ", ".join(closed.mapped("name"))
                )
        return super().write(vals)

    def unlink(self):
        if any(period.state == "closed" for period in self):
            raise UserError(_("A closed period cannot be deleted."))
        self.rate_id.unlink()
        return super().unlink()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_confirm(self):
        """Publish the rate to Odoo so every other feature uses it."""
        for period in self:
            if period.state != "draft":
                raise UserError(
                    _("Only a draft period can be confirmed.")
                )
            period._publish_rate()
            period.state = "confirmed"

    def action_close(self):
        for period in self:
            if period.state != "confirmed":
                raise UserError(
                    _("Only a confirmed period can be closed.")
                )
            period.state = "closed"

    def action_reopen(self):
        """Closing is meant to be final, so reopening is deliberate."""
        for period in self:
            if period.state != "closed":
                raise UserError(_("Only a closed period can be reopened."))
            period.state = "confirmed"

    def action_reset_draft(self):
        for period in self:
            if period.state == "closed":
                raise UserError(
                    _("Reopen %s before returning it to draft.") % period.name
                )
            period.rate_id.unlink()
            period.state = "draft"

    def _publish_rate(self):
        """Create or update the ordinary Odoo rate for this period.

        Rates belong to the root company, which is where Odoo's own default
        puts them; anything else and multi-company setups stop finding them.
        """
        self.ensure_one()
        company = self.company_id.root_id or self.company_id
        values = {
            "name": self.date_from,
            "currency_id": self.currency_id.id,
            "company_id": company.id,
            "rate": self.rate,
        }

        if self.rate_id:
            self.rate_id.write(values)
            return self.rate_id

        existing = self.env["res.currency.rate"].search([
            ("name", "=", self.date_from),
            ("currency_id", "=", self.currency_id.id),
            ("company_id", "=", company.id),
        ], limit=1)

        # Only one rate per currency per day is allowed, so reuse any rate
        # already sitting on this date instead of colliding with it.
        if existing:
            existing.write(values)
            self.rate_id = existing
        else:
            self.rate_id = self.env["res.currency.rate"].create(values)
        return self.rate_id

    # ------------------------------------------------------------------
    # Public helpers, for other modules
    # ------------------------------------------------------------------

    @api.model
    def _period_for(self, date, company=None, currency=None):
        """The period covering a date, or an empty recordset."""
        if not date:
            return self.browse()
        company = company or self.env.company
        currency = currency or company.af_secondary_currency_id
        if not currency:
            return self.browse()
        return self.search([
            ("company_id", "=", company.id),
            ("currency_id", "=", currency.id),
            ("date_from", "<=", date),
            ("date_to", ">=", date),
            ("state", "in", ("confirmed", "closed")),
        ], limit=1)

    @api.model
    def _convert(self, amount, date, company=None, currency=None):
        """Convert from company currency to the second currency.

        :return: ``(converted_amount, period)``. The period is empty when no
            confirmed period covers the date, and the amount is then zero --
            deliberately, so a missing rate is visible rather than silently
            producing a wrong number.
        """
        period = self._period_for(date, company=company, currency=currency)
        if not period:
            return 0.0, period
        return period.currency_id.round(amount * period.rate), period

    @api.model
    def create_monthly_periods(self, year, rate, company=None, currency=None):
        """Create twelve draft periods for a Gregorian year.

        Convenience for setting up a year in one go; the rates are expected to
        be corrected month by month before each is confirmed.
        """
        company = company or self.env.company
        currency = currency or company.af_secondary_currency_id
        if not currency:
            raise UserError(
                _("Set a second currency on %s first.") % company.display_name
            )

        periods = self.browse()
        for month in range(1, 13):
            start = fields.Date.to_date("%04d-%02d-01" % (year, month))
            end = start + relativedelta(months=1, days=-1)
            periods |= self.create({
                "name": "%04d-%02d" % (year, month),
                "company_id": company.id,
                "currency_id": currency.id,
                "date_from": start,
                "date_to": end,
                "rate": rate,
            })
        return periods
