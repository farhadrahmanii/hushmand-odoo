# Part of af_l10n_base. See LICENSE file for full copyright and licensing details.
"""Afghan provinces are stored as Odoo country states.

That choice matters: it means provinces work in every address field Odoo
already has -- partners, employees, invoices, delivery addresses -- with no
extra code anywhere. The alternative, a standalone province model, would have
been isolated from all of it.

The core ``name`` field is not translatable, so the Dari and Pashto names live
in fields added here.
"""

from odoo import api, fields, models


class ResCountryState(models.Model):
    _inherit = "res.country.state"

    af_name_dr = fields.Char(string="Name (Dari)")
    af_name_ps = fields.Char(string="Name (Pashto)")

    @api.depends_context("lang")
    def _compute_display_name(self):
        """Show Afghan provinces in Dari or Pashto when the user reads those.

        Only Afghan states with a translated name are affected; every other
        country keeps Odoo's own behaviour untouched, including the
        "Name (COUNTRY)" form used in some contexts.
        """
        super()._compute_display_name()

        lang = self.env.context.get("lang") or "en_US"
        if not (lang.startswith("fa") or lang.startswith("ps")):
            return

        for state in self:
            local = state.af_name_ps if lang.startswith("ps") else state.af_name_dr
            if lang.startswith("ps") and not local:
                local = state.af_name_dr
            if local:
                state.display_name = local
