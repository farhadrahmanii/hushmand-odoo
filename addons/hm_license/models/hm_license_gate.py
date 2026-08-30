# Part of hm_license. See LICENSE file for full copyright and licensing details.
"""The gate a paid module puts on its own documents.

Inherit the mixin and the model stops accepting new work once the licence has
lapsed::

    class Payslip(models.Model):
        _name = "hm.payslip"
        _inherit = ["hm.payslip", "hm.license.gate"]

        _licence_module = "hm_payroll"

What the gate does, and deliberately does not do
------------------------------------------------

It blocks ``create`` and ``write``. It does **not** block reading, printing,
exporting or unlinking. An unlicensed database therefore becomes read-only in
the modules it has not paid for: every payslip, contract and report the
customer already produced stays visible and printable forever.

That asymmetry is the point. Holding a customer's own historical data hostage
is the behaviour that gets a supplier talked about, and it converts a lapsed
renewal into a dispute. Refusing *new* work is enough pressure, and it is
pressure the customer can relieve by paying.

When the gate is inert
----------------------

* On a development checkout, where no vendor public key has been set. See
  :meth:`~odoo.addons.hm_license.models.hm_license.HmLicense.enforced`.
* While the registry is loading -- installing or upgrading a module runs
  ``create`` for every record in its data and demo files, long before anybody
  could have entered a licence.
"""

from odoo import api, models


class HmLicenseGate(models.AbstractModel):
    _name = "hm.license.gate"
    _description = "Licence-Gated Document"

    #: Which module a licence must cover for this model to accept new work.
    #: Left unset it falls back to the module that declared the model, which
    #: is right in every case in this catalogue but wrong the first time a
    #: module gates a model it inherited from another one -- so set it.
    _licence_module = None

    def _licence_gate_check(self):
        """Refuse the write unless the licence covers this module."""
        if not self.env.registry.ready:
            # Installing or upgrading. There is no licence yet by definition.
            return
        licence = self.env["hm.license"]
        if not licence.enforced():
            return
        licence.require(self._licence_module or self._original_module)

    @api.model_create_multi
    def create(self, vals_list):
        self._licence_gate_check()
        return super().create(vals_list)

    def write(self, vals):
        self._licence_gate_check()
        return super().write(vals)
