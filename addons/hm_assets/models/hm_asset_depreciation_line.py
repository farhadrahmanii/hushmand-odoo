# Part of hm_assets. See LICENSE file for full copyright and licensing details.
"""One depreciation period.

A line is a forecast until it is posted. Posting writes a journal entry and
locks the line, because once a figure is in the ledger it is no longer
something this module gets to change.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HmAssetDepreciationLine(models.Model):
    _name = "hm.asset.depreciation.line"
    _description = "Depreciation Period"
    _order = "asset_id, sequence, date, id"

    asset_id = fields.Many2one(
        comodel_name="hm.asset",
        string="Asset",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        related="asset_id.company_id", store=True, readonly=True,
    )
    currency_id = fields.Many2one(
        related="asset_id.currency_id", readonly=True,
    )
    sequence = fields.Integer(string="#", default=1)
    date = fields.Date(string="Date", required=True, index=True)
    amount = fields.Monetary(string="Depreciation", required=True)
    remaining_value = fields.Monetary(
        string="Remaining",
        help="Book value after this period, salvage value included.",
    )
    posted = fields.Boolean(string="Posted", default=False, index=True)
    move_id = fields.Many2one(
        comodel_name="account.move",
        string="Journal Entry",
        readonly=True,
        ondelete="set null",
        index="btree_not_null",
    )

    # ------------------------------------------------------------------
    # Posting
    # ------------------------------------------------------------------

    def action_post(self):
        """Write this period to the ledger."""
        for line in self:
            if line.posted:
                raise UserError(
                    _("Period %(n)s of %(asset)s is already posted.")
                    % {"n": line.sequence, "asset": line.asset_id.display_name}
                )
            if line.asset_id.state != "running":
                raise UserError(
                    _("%s is not running. Confirm it first.")
                    % line.asset_id.display_name
                )
            line.asset_id._check_accounts()
            move = line._create_move()
            line.write({"posted": True, "move_id": move.id})
            line.asset_id.message_post(
                body=_("Period %(n)s posted: %(amount)s")
                % {
                    "n": line.sequence,
                    "amount": line.currency_id.format(line.amount),
                }
            )
        return True

    def action_post_due(self):
        """Post everything scheduled up to today, and nothing after it.

        Deliberately not a cron. An accountant decides when a period is
        closed; software should not put entries into the ledger on its own.
        """
        today = fields.Date.context_today(self)
        due = self.filtered(lambda l: not l.posted and l.date <= today)
        if not due:
            raise UserError(_("Nothing is due yet."))
        return due.action_post()

    def _create_move(self):
        """Debit the expense, credit accumulated depreciation."""
        self.ensure_one()
        asset = self.asset_id
        label = _("Depreciation %(n)s: %(asset)s") % {
            "n": self.sequence, "asset": asset.name,
        }
        return self.env["account.move"].create({
            "move_type": "entry",
            "journal_id": asset.journal_id.id,
            "date": self.date,
            "ref": asset.code or asset.name,
            "company_id": asset.company_id.id,
            "line_ids": [
                (0, 0, {
                    "name": label,
                    "account_id": asset.account_expense_id.id,
                    "debit": self.amount,
                    "credit": 0.0,
                    "partner_id": asset.partner_id.id or False,
                }),
                (0, 0, {
                    "name": label,
                    "account_id": asset.account_depreciation_id.id,
                    "debit": 0.0,
                    "credit": self.amount,
                    "partner_id": asset.partner_id.id or False,
                }),
            ],
        })

    # ------------------------------------------------------------------
    # Guards
    # ------------------------------------------------------------------

    def unlink(self):
        if any(line.posted for line in self):
            raise UserError(
                _("A posted period cannot be deleted. Reverse its journal "
                  "entry instead, so the ledger keeps a record of both.")
            )
        return super().unlink()

    def write(self, vals):
        protected = {"amount", "date", "sequence"}
        if protected & set(vals):
            posted = self.filtered("posted")
            if posted:
                raise UserError(
                    _("Period %s is posted and cannot be changed.")
                    % ", ".join(str(l.sequence) for l in posted)
                )
        return super().write(vals)

    @api.depends("sequence", "asset_id.name")
    def _compute_display_name(self):
        for line in self:
            line.display_name = "%s / %s" % (
                line.asset_id.name or "", line.sequence
            )
