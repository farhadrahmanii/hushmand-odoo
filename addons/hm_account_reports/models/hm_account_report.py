# Part of hm_account_reports. See LICENSE file for full copyright and licensing details.
"""Financial statements for Odoo Community.

Community ships journal items and a chart of accounts but no statements: no
trial balance, no profit and loss, no balance sheet. Odoo's dynamic reports
are Enterprise, so a Community user who needs to file accounts or hand
something to an auditor has nothing to hand them.

This computes the three that every accountant asks for first, straight from
``account.move.line``.

A note on signs. Odoo stores ``balance`` as debit minus credit, so income,
liability and equity accounts carry negative balances. A statement is expected
to show them as positive figures, so those groups are negated on the way out.
Doing it in one place, here, keeps the templates from having to think about it.
"""

from odoo import _, api, models

#: The five groups a statement cares about, derived from account_type.
#: ``internal_group`` on account.account is computed rather than stored, so it
#: cannot be grouped on; the prefix of account_type gives the same answer and
#: is indexed.
GROUP_ASSET = "asset"
GROUP_LIABILITY = "liability"
GROUP_EQUITY = "equity"
GROUP_INCOME = "income"
GROUP_EXPENSE = "expense"
GROUP_OFF = "off"

#: Groups shown as positive figures despite carrying a credit balance.
CREDIT_GROUPS = (GROUP_LIABILITY, GROUP_EQUITY, GROUP_INCOME)

#: Groups whose balance carries forward across financial years. Income and
#: expense accounts reset, which is why a trial balance shows no opening
#: figure for them.
CARRY_FORWARD_GROUPS = (GROUP_ASSET, GROUP_LIABILITY, GROUP_EQUITY)

#: The order sections appear in, as account_type keys only.
#: The labels are deliberately NOT built here: calling _() at import time has
#: no environment to resolve a language from, so Odoo cannot translate it and
#: logs a warning. Labels are produced by _section_label at call time instead.
BALANCE_SHEET_ORDER = [
    "asset_current",
    "asset_receivable",
    "asset_cash",
    "asset_prepayments",
    "asset_fixed",
    "asset_non_current",
    "liability_payable",
    "liability_credit_card",
    "liability_current",
    "liability_non_current",
    "equity",
    "equity_unaffected",
]

PROFIT_LOSS_ORDER = [
    "income",
    "income_other",
    "expense_direct_cost",
    "expense",
    "expense_depreciation",
    "expense_other",
]


def account_group(account_type):
    """The statement group an account type belongs to.

    ``asset_receivable`` gives ``asset``, ``equity_unaffected`` gives
    ``equity``, ``off_balance`` gives ``off``.
    """
    return (account_type or "").split("_", 1)[0]


class HmAccountReport(models.AbstractModel):
    _name = "hm.account.report"
    _description = "Financial Report Engine"

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    @api.model
    def _base_domain(self, options, date_from=None, date_to=None):
        """The move-line domain shared by every report."""
        domain = [
            ("company_id", "in", options["company_ids"]),
            ("account_id.account_type", "!=", "off_balance"),
        ]
        if options.get("posted_only", True):
            domain.append(("parent_state", "=", "posted"))
        else:
            domain.append(("parent_state", "in", ("posted", "draft")))

        if date_from:
            domain.append(("date", ">=", date_from))
        if date_to:
            domain.append(("date", "<=", date_to))
        if options.get("journal_ids"):
            domain.append(("journal_id", "in", options["journal_ids"]))
        if options.get("analytic_account_id"):
            # analytic_distribution is a JSON map of account id to percentage.
            domain.append((
                "analytic_distribution",
                "in",
                [options["analytic_account_id"]],
            ))
        return domain

    @api.model
    def _totals_by_account(self, options, date_from=None, date_to=None):
        """``{account_id: {"debit": x, "credit": y, "balance": z}}``."""
        groups = self.env["account.move.line"]._read_group(
            self._base_domain(options, date_from, date_to),
            groupby=["account_id"],
            aggregates=["debit:sum", "credit:sum", "balance:sum"],
        )
        return {
            account.id: {
                "debit": debit or 0.0,
                "credit": credit or 0.0,
                "balance": balance or 0.0,
            }
            for account, debit, credit, balance in groups
        }

    # ------------------------------------------------------------------
    # Trial balance
    # ------------------------------------------------------------------

    @api.model
    def trial_balance(self, options):
        """Opening, movement and closing figures per account.

        Only balance-sheet accounts get an opening figure. Income and expense
        accounts reset each financial year, so showing them a brought-forward
        balance would be wrong.
        """
        period = self._totals_by_account(
            options, options["date_from"], options["date_to"]
        )
        opening = self._totals_by_account(options, None, options["date_from_before"])

        account_ids = set(period) | set(opening)
        accounts = self.env["account.account"].browse(account_ids).sorted(
            lambda a: (a.code or "", a.name or "")
        )

        lines = []
        totals = {"opening": 0.0, "debit": 0.0, "credit": 0.0, "closing": 0.0}

        for account in accounts:
            group = account_group(account.account_type)
            moved = period.get(account.id, {})
            opened = opening.get(account.id, {})

            initial = (
                opened.get("balance", 0.0)
                if group in CARRY_FORWARD_GROUPS
                else 0.0
            )
            debit = moved.get("debit", 0.0)
            credit = moved.get("credit", 0.0)
            closing = initial + moved.get("balance", 0.0)

            if options.get("hide_zero") and not any((initial, debit, credit, closing)):
                continue

            lines.append({
                "account_id": account.id,
                "code": account.code or "",
                "name": account.name or "",
                "account_type": account.account_type,
                "group": group,
                "opening": initial,
                "debit": debit,
                "credit": credit,
                "closing": closing,
            })
            totals["opening"] += initial
            totals["debit"] += debit
            totals["credit"] += credit
            totals["closing"] += closing

        return {"lines": lines, "totals": totals}

    # ------------------------------------------------------------------
    # Profit and loss
    # ------------------------------------------------------------------

    @api.model
    def profit_and_loss(self, options):
        period = self._totals_by_account(
            options, options["date_from"], options["date_to"]
        )
        sections = self._sections(period, PROFIT_LOSS_ORDER, options)

        income = sum(
            s["total"] for s in sections
            if account_group(s["account_type"]) == GROUP_INCOME
        )
        expense = sum(
            s["total"] for s in sections
            if account_group(s["account_type"]) == GROUP_EXPENSE
        )

        return {
            "sections": sections,
            "income_total": income,
            "expense_total": expense,
            "net_result": income - expense,
        }

    # ------------------------------------------------------------------
    # Balance sheet
    # ------------------------------------------------------------------

    @api.model
    def balance_sheet(self, options):
        """Positions as at the end date, with this period's result as equity.

        The current-year result is not sitting in an account yet -- that only
        happens when the year is closed -- so it is computed and added to
        equity. Without it the sheet does not balance, which is the first
        thing anyone checks.
        """
        cumulative = self._totals_by_account(options, None, options["date_to"])
        sections = self._sections(cumulative, BALANCE_SHEET_ORDER, options)

        assets = sum(
            s["total"] for s in sections
            if account_group(s["account_type"]) == GROUP_ASSET
        )
        liabilities = sum(
            s["total"] for s in sections
            if account_group(s["account_type"]) == GROUP_LIABILITY
        )
        equity = sum(
            s["total"] for s in sections
            if account_group(s["account_type"]) == GROUP_EQUITY
        )

        result = self.profit_and_loss(options)["net_result"]
        equity_with_result = equity + result

        return {
            "sections": sections,
            "assets_total": assets,
            "liabilities_total": liabilities,
            "equity_total": equity_with_result,
            "current_result": result,
            "liabilities_and_equity": liabilities + equity_with_result,
            "balanced": self.env.company.currency_id.is_zero(
                assets - (liabilities + equity_with_result)
            ),
        }

    # ------------------------------------------------------------------
    # Shared
    # ------------------------------------------------------------------

    @api.model
    def _section_label(self, account_type):
        """A human label for a section, translated when it is actually used."""
        labels = {
            "asset_current": _("Current Assets"),
            "asset_receivable": _("Receivables"),
            "asset_cash": _("Bank and Cash"),
            "asset_prepayments": _("Prepayments"),
            "asset_fixed": _("Fixed Assets"),
            "asset_non_current": _("Non-current Assets"),
            "liability_payable": _("Payables"),
            "liability_credit_card": _("Credit Card"),
            "liability_current": _("Current Liabilities"),
            "liability_non_current": _("Non-current Liabilities"),
            "equity": _("Equity"),
            "equity_unaffected": _("Previous Years Earnings"),
            "income": _("Operating Income"),
            "income_other": _("Other Income"),
            "expense_direct_cost": _("Cost of Revenue"),
            "expense": _("Operating Expenses"),
            "expense_depreciation": _("Depreciation"),
            "expense_other": _("Other Expenses"),
        }
        return labels.get(account_type, account_type)

    @api.model
    def _sections(self, totals, order, options):
        """Group account totals into the sections a statement presents."""
        accounts = self.env["account.account"].browse(totals.keys())
        by_type = {}
        for account in accounts:
            by_type.setdefault(account.account_type, self.env["account.account"])
            by_type[account.account_type] |= account

        sections = []
        for account_type in order:
            label = self._section_label(account_type)
            in_section = by_type.get(account_type)
            if not in_section:
                continue

            group = account_group(account_type)
            sign = -1.0 if group in CREDIT_GROUPS else 1.0

            lines = []
            section_total = 0.0
            for account in in_section.sorted(lambda a: (a.code or "", a.name or "")):
                amount = totals[account.id]["balance"] * sign
                if options.get("hide_zero") and not amount:
                    continue
                lines.append({
                    "account_id": account.id,
                    "code": account.code or "",
                    "name": account.name or "",
                    "amount": amount,
                })
                section_total += amount

            if not lines:
                continue
            sections.append({
                "account_type": account_type,
                "label": label,
                "lines": lines,
                "total": section_total,
            })
        return sections
