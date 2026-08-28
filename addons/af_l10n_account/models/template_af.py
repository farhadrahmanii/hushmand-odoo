# Part of af_l10n_account. See LICENSE file for full copyright and licensing details.
"""Afghanistan chart of accounts.

Odoo ships 225 fiscal localizations and Afghanistan is not among them, in
either edition. An Afghan company installing Odoo today has to build a chart
from nothing, and gets the tax treatment wrong on the way.

There is no chart of accounts mandated for private companies in Afghanistan,
so this is a conventional structure adapted to what Afghan businesses and
NGOs actually record: dual AFN and USD cash, staff advances, and separate
withholding accounts for salaries, rent and contractors, because those are
filed separately.
"""

from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template("af")
    def _get_af_template_data(self):
        return {
            "name": "Afghanistan",
            "code_digits": "6",
            "property_account_receivable_id": "af_101001",
            "property_account_payable_id": "af_200101",
            "property_account_expense_categ_id": "af_500101",
            "property_account_income_categ_id": "af_400101",
        }

    @template("af", "res.company")
    def _get_af_res_company(self):
        return {
            self.env.company.id: {
                "account_fiscal_country_id": "base.af",
                "bank_account_code_prefix": "1003",
                "cash_account_code_prefix": "1002",
                "transfer_account_code_prefix": "1001",
                "account_default_pos_receivable_account_id": "af_101002",
                "account_journal_suspense_account_id": "af_100102",
                "transfer_account_id": "af_100101",
                "income_currency_exchange_account_id": "af_400301",
                "expense_currency_exchange_account_id": "af_500901",
                "default_cash_difference_income_account_id": "af_400302",
                "default_cash_difference_expense_account_id": "af_500902",
                "account_journal_early_pay_discount_gain_account_id": "af_400303",
                "account_journal_early_pay_discount_loss_account_id": "af_500903",
                "account_sale_tax_id": "af_brt_sale_2",
                "account_purchase_tax_id": "af_exempt_purchase",
                "income_account_id": "af_400101",
                "expense_account_id": "af_500101",
            },
        }
