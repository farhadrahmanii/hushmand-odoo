# Part of hm_expiry_docs. See LICENSE file for full copyright and licensing details.
"""Documents that expire, and reminders that reach somebody.

Every organisation tracks things with an expiry date -- licences, permits,
visas, insurance, certifications, registrations -- and most track them in a
spreadsheet that nobody opens until something has already lapsed.

The model is deliberately generic. One document type covers a work permit and
another covers a vehicle registration, without either needing its own model,
its own views or its own reminder logic. Six near-identical models would have
been six places to fix the same bug.
"""

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class HmExpiryDocumentType(models.Model):
    _name = "hm.expiry.document.type"
    _description = "Document Type"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    code = fields.Char(help="Short code used on lists and references.")
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        help="Leave empty to share across companies.",
    )

    validity_months = fields.Integer(
        string="Usual Validity",
        default=12,
        help="Months a document of this type is normally valid for. Used to "
             "suggest an expiry date; it can always be overridden.",
    )
    reminder_days = fields.Integer(
        string="Remind Before",
        default=30,
        help="Days before expiry to raise an activity for the responsible "
             "person.",
    )
    requires_number = fields.Boolean(
        string="Number Required",
        default=True,
        help="A passport has a number; a signed undertaking may not.",
    )
    document_count = fields.Integer(compute="_compute_document_count")
    expiring_count = fields.Integer(compute="_compute_document_count")

    _reminder_positive = models.Constraint(
        "CHECK (reminder_days >= 0)",
        "The reminder period cannot be negative.",
    )

    def _compute_document_count(self):
        Document = self.env["hm.expiry.document"]
        totals = dict(Document._read_group(
            [("type_id", "in", self.ids)],
            groupby=["type_id"], aggregates=["__count"],
        ))
        expiring = dict(Document._read_group(
            [("type_id", "in", self.ids), ("state", "in", ("expiring", "expired"))],
            groupby=["type_id"], aggregates=["__count"],
        ))
        for record in self:
            record.document_count = totals.get(record, 0)
            record.expiring_count = expiring.get(record, 0)

    def action_view_documents(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.display_name,
            "res_model": "hm.expiry.document",
            "view_mode": "list,form",
            "domain": [("type_id", "=", self.id)],
            "context": {"default_type_id": self.id},
        }


class HmExpiryDocument(models.Model):
    _name = "hm.expiry.document"
    _description = "Expiring Document"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_expiry, id"

    name = fields.Char(
        string="Number",
        tracking=True,
        help="The document's own number or reference.",
    )
    type_id = fields.Many2one(
        comodel_name="hm.expiry.document.type",
        string="Type",
        required=True,
        tracking=True,
        index=True,
    )
    subject = fields.Char(
        string="Held By",
        tracking=True,
        help="Who or what the document belongs to, when that is not a "
             "contact -- a vehicle, a building, the company itself.",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Contact",
        tracking=True,
        index="btree_not_null",
    )
    responsible_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        default=lambda self: self.env.user,
        tracking=True,
        help="Who gets the reminder. A document nobody owns is a document "
             "nobody renews.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )

    date_issue = fields.Date(string="Issued", tracking=True)
    date_expiry = fields.Date(string="Expires", required=True, tracking=True, index=True)
    issuing_authority = fields.Char(string="Issued By")
    notes = fields.Text()

    days_to_expiry = fields.Integer(
        string="Days Left",
        compute="_compute_expiry_state",
        help="Negative once the document has lapsed.",
    )
    state = fields.Selection(
        selection=[
            ("valid", "Valid"),
            ("expiring", "Expiring Soon"),
            ("expired", "Expired"),
            ("renewed", "Renewed"),
            ("cancelled", "Cancelled"),
        ],
        compute="_compute_expiry_state",
        store=True,
        index=True,
        tracking=True,
        help="Valid, expiring and expired follow the dates. Renewed and "
             "cancelled are set by hand and stop the reminders.",
    )
    manual_state = fields.Selection(
        selection=[("renewed", "Renewed"), ("cancelled", "Cancelled")],
        string="Closed As",
        copy=False,
        help="Set when a document is superseded or withdrawn. Overrides the "
             "date-driven status.",
    )

    renewed_from_id = fields.Many2one(
        comodel_name="hm.expiry.document",
        string="Renews",
        readonly=True,
        copy=False,
        help="The document this one replaces.",
    )
    renewal_ids = fields.One2many(
        comodel_name="hm.expiry.document",
        inverse_name="renewed_from_id",
        string="Renewed By",
    )
    reminder_sent = fields.Boolean(
        string="Reminder Raised", default=False, copy=False, readonly=True,
    )

    _expiry_after_issue = models.Constraint(
        "CHECK (date_issue IS NULL OR date_issue <= date_expiry)",
        "A document cannot expire before it was issued.",
    )

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    @api.depends("date_expiry", "manual_state", "type_id.reminder_days")
    def _compute_expiry_state(self):
        today = fields.Date.context_today(self)
        for document in self:
            if document.date_expiry:
                document.days_to_expiry = (document.date_expiry - today).days
            else:
                document.days_to_expiry = 0

            if document.manual_state:
                document.state = document.manual_state
                continue

            lead = document.type_id.reminder_days or 0
            if document.days_to_expiry < 0:
                document.state = "expired"
            elif document.days_to_expiry <= lead:
                document.state = "expiring"
            else:
                document.state = "valid"

    @api.constrains("name", "type_id")
    def _check_number_required(self):
        for document in self:
            if document.type_id.requires_number and not document.name:
                raise ValidationError(
                    _("%s needs a document number.") % document.type_id.name
                )

    @api.depends("name", "type_id", "subject", "partner_id")
    def _compute_display_name(self):
        for document in self:
            holder = document.partner_id.display_name or document.subject or ""
            parts = [document.type_id.name or ""]
            if document.name:
                parts.append(document.name)
            label = " ".join(p for p in parts if p)
            document.display_name = (
                "%s - %s" % (label, holder) if holder else label
            )

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------

    @api.onchange("type_id", "date_issue")
    def _onchange_suggest_expiry(self):
        """Suggest an expiry date, never overwrite one already entered."""
        for document in self:
            if document.date_expiry or not document.date_issue:
                continue
            months = document.type_id.validity_months
            if months:
                document.date_expiry = document.date_issue + relativedelta(
                    months=months, days=-1
                )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_renew(self):
        """Open a new document that supersedes this one."""
        self.ensure_one()
        if self.manual_state:
            raise UserError(
                _("%s is already closed.") % self.display_name
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("Renew"),
            "res_model": "hm.expiry.document",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_type_id": self.type_id.id,
                "default_partner_id": self.partner_id.id,
                "default_subject": self.subject,
                "default_responsible_id": self.responsible_id.id,
                "default_issuing_authority": self.issuing_authority,
                "default_renewed_from_id": self.id,
                "default_date_issue": fields.Date.context_today(self),
            },
        }

    def action_mark_cancelled(self):
        for document in self:
            document.manual_state = "cancelled"
            document._clear_activities()

    def action_reopen(self):
        for document in self:
            document.manual_state = False

    # ------------------------------------------------------------------
    # Reminders
    # ------------------------------------------------------------------

    @api.model
    def _cron_raise_reminders(self, limit=500):
        """Raise an activity for anything close to expiry or already lapsed.

        Called daily. Only documents that have not already been reminded are
        touched, so a person gets one activity per document rather than one
        every morning until they act -- which is how reminders get ignored.
        """
        today = fields.Date.context_today(self)

        # state is stored but derived from today's date, so it does not change
        # on its own as time passes: a document saved as valid would still read
        # valid long after it lapsed. Force a recompute for everything still
        # open before deciding who to remind.
        open_documents = self.search([("manual_state", "=", False)])
        if open_documents:
            self.env.add_to_compute(self._fields["state"], open_documents)
            open_documents.flush_recordset(["state"])

        candidates = self.search(
            [
                ("manual_state", "=", False),
                ("reminder_sent", "=", False),
                ("responsible_id", "!=", False),
            ],
            limit=limit,
        )

        raised = self.browse()
        for document in candidates:
            lead = document.type_id.reminder_days or 0
            days_left = (document.date_expiry - today).days
            if days_left > lead:
                continue
            document._raise_reminder(days_left)
            raised |= document

        raised.write({"reminder_sent": True})
        return len(raised)

    def _raise_reminder(self, days_left):
        self.ensure_one()
        if days_left < 0:
            summary = _("Expired: %s") % self.display_name
            note = _("%(document)s expired %(days)s day(s) ago.") % {
                "document": self.display_name, "days": abs(days_left),
            }
        else:
            summary = _("Expiring: %s") % self.display_name
            note = _("%(document)s expires in %(days)s day(s), on %(date)s.") % {
                "document": self.display_name,
                "days": days_left,
                "date": self.date_expiry,
            }
        # sudo: the scheduler runs as a system user and must be able to raise
        # an activity for whoever is responsible, regardless of its own rights
        # over the record.
        self.sudo().activity_schedule(
            user_id=self.responsible_id.id,
            date_deadline=self.date_expiry,
            summary=summary,
            note=note,
        )

    def _clear_activities(self):
        for document in self:
            activities = self.env["mail.activity"].sudo().search([
                ("res_model", "=", "hm.expiry.document"),
                ("res_id", "=", document.id),
            ])
            activities.unlink()

    # ------------------------------------------------------------------
    # Renewal bookkeeping
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        documents = super().create(vals_list)
        for document in documents:
            previous = document.renewed_from_id
            if previous:
                previous.write({"manual_state": "renewed"})
                previous._clear_activities()
                previous.message_post(
                    body=_("Renewed by %s.") % document.display_name
                )
        return documents

    def write(self, vals):
        # A new expiry date means the old reminder no longer applies.
        if "date_expiry" in vals:
            self._clear_activities()
            vals.setdefault("reminder_sent", False)
        return super().write(vals)

