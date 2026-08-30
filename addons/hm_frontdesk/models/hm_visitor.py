# Part of hm_frontdesk. See LICENSE file for full copyright and licensing details.
"""Visitor register.

Odoo's Frontdesk is Enterprise, so a Community user has nowhere to record who
came into the building. Most offices fall back to a paper book at the desk,
which answers "who is here right now?" only by reading every page.

Two things this is built around:

* **Who is in the building** has to be answerable instantly, because that is
  the question asked during a fire drill or an incident, not afterwards.
* **A visitor who is never checked out** is the normal failure of a paper
  book. Those are surfaced rather than left to accumulate silently.
"""

from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HmVisitor(models.Model):
    _name = "hm.visitor"
    _description = "Visitor"
    _inherit = ["mail.thread", "mail.activity.mixin", "hm.license.gate"]
    _licence_module = "hm_frontdesk"
    _order = "check_in desc, expected_date desc, id desc"

    name = fields.Char(string="Visitor", required=True, tracking=True)
    organisation = fields.Char(string="Organisation")
    phone = fields.Char(string="Phone")
    email = fields.Char(string="Email")
    id_document = fields.Char(
        string="ID Presented",
        help="Whatever identification was shown at the desk, and its number.",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Contact",
        index="btree_not_null",
        help="If the visitor is already a known contact.",
    )

    host_id = fields.Many2one(
        comodel_name="res.users",
        string="Host",
        tracking=True,
        index="btree_not_null",
        help="Who they are here to see. The host is notified on arrival.",
    )
    purpose = fields.Char(string="Purpose", tracking=True)
    location = fields.Char(
        string="Going To",
        help="Floor, room or department, so the desk knows where they went.",
    )

    expected_date = fields.Datetime(
        string="Expected",
        tracking=True,
        help="Set when a visit is arranged in advance.",
    )
    check_in = fields.Datetime(string="Checked In", readonly=True, tracking=True)
    check_out = fields.Datetime(string="Checked Out", readonly=True, tracking=True)
    duration_minutes = fields.Integer(
        string="Minutes On Site", compute="_compute_duration", store=True,
    )

    badge_number = fields.Char(string="Badge", tracking=True)
    vehicle_plate = fields.Char(string="Vehicle")
    accompanying_count = fields.Integer(
        string="Accompanying",
        default=0,
        help="How many others came in with them.",
    )

    state = fields.Selection(
        selection=[
            ("expected", "Expected"),
            ("on_site", "On Site"),
            ("left", "Left"),
            ("cancelled", "Cancelled"),
        ],
        default="expected",
        required=True,
        tracking=True,
        index=True,
    )
    notes = fields.Text()
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )

    _accompanying_not_negative = models.Constraint(
        "CHECK (accompanying_count >= 0)",
        "The number accompanying cannot be negative.",
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------

    @api.depends("check_in", "check_out")
    def _compute_duration(self):
        for visitor in self:
            if visitor.check_in and visitor.check_out:
                delta = visitor.check_out - visitor.check_in
                visitor.duration_minutes = int(delta.total_seconds() // 60)
            else:
                visitor.duration_minutes = 0

    @api.depends("name", "organisation")
    def _compute_display_name(self):
        for visitor in self:
            visitor.display_name = (
                "%s (%s)" % (visitor.name, visitor.organisation)
                if visitor.organisation else visitor.name or ""
            )

    # ------------------------------------------------------------------
    # The desk
    # ------------------------------------------------------------------

    def action_check_in(self):
        for visitor in self:
            if visitor.state == "on_site":
                raise UserError(
                    _("%s is already checked in.") % visitor.display_name
                )
            if visitor.state == "left":
                raise UserError(
                    _("%s has already left. Register a new visit.")
                    % visitor.display_name
                )
            visitor.write({
                "state": "on_site",
                "check_in": fields.Datetime.now(),
                "check_out": False,
            })
            visitor._notify_host()

    def action_check_out(self):
        for visitor in self:
            if visitor.state != "on_site":
                raise UserError(
                    _("%s is not on site.") % visitor.display_name
                )
            visitor.write({
                "state": "left",
                "check_out": fields.Datetime.now(),
            })

    def action_cancel(self):
        for visitor in self:
            if visitor.state == "on_site":
                raise UserError(
                    _("%s is on site. Check them out rather than cancelling "
                      "the visit.") % visitor.display_name
                )
            visitor.state = "cancelled"

    def action_reset_expected(self):
        for visitor in self:
            if visitor.state == "on_site":
                raise UserError(_("Check the visitor out first."))
            visitor.write({
                "state": "expected",
                "check_in": False,
                "check_out": False,
            })

    def _notify_host(self):
        """Tell the host their visitor has arrived."""
        for visitor in self:
            if not visitor.host_id:
                continue
            # sudo: the person on the desk should not need write access to the
            # host's records in order to tell them somebody is waiting.
            visitor.sudo().message_post(
                body=_("%(visitor)s has arrived at reception.")
                % {"visitor": visitor.display_name},
                partner_ids=visitor.host_id.partner_id.ids,
            )

    # ------------------------------------------------------------------
    # Housekeeping
    # ------------------------------------------------------------------

    @api.model
    def _cron_flag_overnight_visitors(self):
        """Surface visitors still on site from a previous day.

        A paper book's usual failure is a visitor who is never checked out.
        Rather than closing them automatically -- which would invent a
        departure time nobody observed -- the record is left open and the host
        is asked, so the register keeps saying "we do not know" until somebody
        answers.
        """
        cutoff = fields.Datetime.now() - timedelta(days=1)
        stale = self.search([
            ("state", "=", "on_site"),
            ("check_in", "<", cutoff),
        ])
        for visitor in stale:
            if not visitor.host_id:
                continue
            visitor.sudo().activity_schedule(
                user_id=visitor.host_id.id,
                summary=_("Visitor never checked out: %s") % visitor.display_name,
                note=_(
                    "%(visitor)s was checked in on %(date)s and has not been "
                    "checked out. Please confirm when they left."
                ) % {
                    "visitor": visitor.display_name,
                    "date": visitor.check_in,
                },
            )
        return len(stale)

    @api.model
    def on_site_count(self):
        """How many people are in the building right now."""
        return self.search_count([("state", "=", "on_site")])
