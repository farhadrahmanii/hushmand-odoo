# Part of hm_approvals. See LICENSE file for full copyright and licensing details.
"""Approval processes and their steps.

Odoo Community has no approval engine. Enterprise has an Approvals app, but it
models a *request for something* -- a standalone record someone raises. It does
not put an approval chain in front of an existing document, which is what an
organisation actually needs: this purchase request, this leave, this contract,
routed to the right people in the right order before it takes effect.

A process is a definition, not an instance. It says which model it governs and
what the steps are. Running one produces an ``hm.approval.request``.
"""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

#: Operators available for a step condition. Deliberately a fixed list rather
#: than an eval: a condition is configuration, and configuration that can run
#: arbitrary code is a security problem waiting to happen.
CONDITION_OPERATORS = [
    ("=", "is equal to"),
    ("!=", "is not equal to"),
    (">", "is greater than"),
    (">=", "is greater than or equal to"),
    ("<", "is less than"),
    ("<=", "is less than or equal to"),
    ("set", "is set"),
    ("not_set", "is not set"),
    ("in", "is one of"),
    ("not_in", "is not one of"),
]


class HmApprovalProcess(models.Model):
    _name = "hm.approval.process"
    _description = "Approval Process"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        help="Leave empty to apply in every company.",
    )
    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Applies To",
        required=True,
        ondelete="cascade",
        help="The document this process approves.",
    )
    model_name = fields.Char(related="model_id.model", store=True, readonly=True)
    step_ids = fields.One2many(
        comodel_name="hm.approval.step",
        inverse_name="process_id",
        string="Steps",
        copy=True,
    )
    step_count = fields.Integer(compute="_compute_step_count")
    request_count = fields.Integer(compute="_compute_request_count")
    description = fields.Text(translate=True)

    _name_model_uniq = models.Constraint(
        "unique(name, model_id, company_id)",
        "A process with this name already exists for that document.",
    )

    @api.depends("step_ids")
    def _compute_step_count(self):
        for process in self:
            process.step_count = len(process.step_ids)

    def _compute_request_count(self):
        counts = dict(
            self.env["hm.approval.request"]._read_group(
                [("process_id", "in", self.ids)],
                groupby=["process_id"],
                aggregates=["__count"],
            )
        )
        for process in self:
            process.request_count = counts.get(process, 0)

    @api.model
    def _process_for(self, record):
        """The process governing a record, or an empty recordset."""
        if not record:
            return self.browse()
        company = getattr(record, "company_id", False) or self.env.company
        return self.search([
            ("model_name", "=", record._name),
            "|", ("company_id", "=", False), ("company_id", "=", company.id),
        ], limit=1)

    def action_view_requests(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Approval Requests"),
            "res_model": "hm.approval.request",
            "view_mode": "list,form",
            "domain": [("process_id", "=", self.id)],
        }


class HmApprovalStep(models.Model):
    _name = "hm.approval.step"
    _description = "Approval Step"
    _order = "process_id, sequence, id"

    name = fields.Char(string="Step", required=True, translate=True)
    sequence = fields.Integer(default=10)
    process_id = fields.Many2one(
        comodel_name="hm.approval.process",
        string="Process",
        required=True,
        ondelete="cascade",
        index=True,
    )
    model_name = fields.Char(related="process_id.model_name", readonly=True)

    # ------------------------------------------------------------------
    # Who approves
    # ------------------------------------------------------------------

    approver_type = fields.Selection(
        selection=[
            ("user", "A specific person"),
            ("group", "Anyone in a group"),
            ("field", "Whoever the document says"),
        ],
        string="Approver",
        default="user",
        required=True,
        help="A field approver is resolved from the document itself, for "
             "example the requester's manager or the project owner, so the "
             "process does not need rewriting when people change roles.",
    )
    approver_user_id = fields.Many2one(
        comodel_name="res.users", string="Person",
    )
    approver_group_id = fields.Many2one(
        comodel_name="res.groups", string="Group",
    )
    approver_field = fields.Char(
        string="Field Path",
        help="A path on the document leading to a user, for example "
             "employee_id.parent_id.user_id or project_id.user_id.",
    )

    # ------------------------------------------------------------------
    # When it applies
    # ------------------------------------------------------------------

    condition_field = fields.Char(
        string="Only When",
        help="A field on the document. Leave empty and the step always runs.",
    )
    condition_operator = fields.Selection(
        selection=CONDITION_OPERATORS, string="Operator", default="=",
    )
    condition_value = fields.Char(string="Value")

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------

    allow_reject = fields.Boolean(string="Can Reject", default=True)
    require_comment = fields.Boolean(
        string="Comment Required",
        help="Require a comment when approving, not only when rejecting.",
    )
    require_comment_on_reject = fields.Boolean(
        string="Reason Required to Reject", default=True,
    )
    approve_label = fields.Char(
        string="Approve Button", translate=True,
        help="Wording for the approve button, for example Verify or Endorse.",
    )

    @api.constrains("approver_type", "approver_user_id", "approver_group_id",
                    "approver_field")
    def _check_approver(self):
        for step in self:
            if step.approver_type == "user" and not step.approver_user_id:
                raise ValidationError(
                    _("Step %s needs a person to approve it.") % step.name
                )
            if step.approver_type == "group" and not step.approver_group_id:
                raise ValidationError(
                    _("Step %s needs a group.") % step.name
                )
            if step.approver_type == "field" and not step.approver_field:
                raise ValidationError(
                    _("Step %s needs a field path.") % step.name
                )

    @api.constrains("approver_field", "process_id")
    def _check_approver_field_resolves(self):
        """Catch a bad path when it is configured, not when someone submits."""
        for step in self:
            if step.approver_type != "field" or not step.approver_field:
                continue
            model = self.env.get(step.process_id.model_name)
            if model is None:
                continue
            current = model
            for part in step.approver_field.split("."):
                if current is None or part not in current._fields:
                    raise ValidationError(
                        _("%(path)s is not a valid path on %(model)s: "
                          "%(part)s does not exist.")
                        % {
                            "path": step.approver_field,
                            "model": step.process_id.model_name,
                            "part": part,
                        }
                    )
                field = current._fields[part]
                current = self.env.get(field.comodel_name) if field.relational else None

    @api.constrains("condition_field", "process_id")
    def _check_condition_field(self):
        for step in self:
            if not step.condition_field:
                continue
            model = self.env.get(step.process_id.model_name)
            if model is not None and step.condition_field not in model._fields:
                raise ValidationError(
                    _("%(field)s is not a field on %(model)s.")
                    % {
                        "field": step.condition_field,
                        "model": step.process_id.model_name,
                    }
                )

    # ------------------------------------------------------------------
    # Runtime
    # ------------------------------------------------------------------

    def _resolve_approvers(self, record):
        """The users who may act on this step for a given document."""
        self.ensure_one()

        if self.approver_type == "user":
            return self.approver_user_id

        if self.approver_type == "group":
            # Odoo 19 renamed res.groups.users to user_ids.
            return self.approver_group_id.user_ids.filtered("active")

        target = record
        for part in self.approver_field.split("."):
            if not target:
                return self.env["res.users"].browse()
            target = target[part]

        if not target:
            return self.env["res.users"].browse()
        if target._name == "res.users":
            return target
        # A path often lands on an employee or a partner; take its user.
        if "user_id" in target._fields and target.user_id:
            return target.user_id
        return self.env["res.users"].browse()

    def _applies_to(self, record):
        """Does this step run for this document?

        A step whose condition is false is skipped, not failed. That is what
        makes a single process able to say "anything over 50,000 also needs
        the director".
        """
        self.ensure_one()
        if not self.condition_field:
            return True

        if self.condition_field not in record._fields:
            # Configuration drifted after the process was written. Run the
            # step rather than silently letting a document through.
            return True

        value = record[self.condition_field]
        field = record._fields[self.condition_field]

        if self.condition_operator == "set":
            return bool(value)
        if self.condition_operator == "not_set":
            return not value

        expected = self._coerce(self.condition_value, field)

        if self.condition_operator in ("in", "not_in"):
            options = [
                self._coerce(part.strip(), field)
                for part in (self.condition_value or "").split(",")
            ]
            if field.relational:
                actual = value.id if value else False
            else:
                actual = value
            return (actual in options) if self.condition_operator == "in" \
                else (actual not in options)

        if field.relational:
            value = value.id if value else False

        try:
            if self.condition_operator == "=":
                return value == expected
            if self.condition_operator == "!=":
                return value != expected
            if self.condition_operator == ">":
                return value > expected
            if self.condition_operator == ">=":
                return value >= expected
            if self.condition_operator == "<":
                return value < expected
            if self.condition_operator == "<=":
                return value <= expected
        except TypeError:
            # Comparing a string to a number, for instance. Treat a condition
            # that cannot be evaluated as true so the step still runs.
            return True
        return True

    @staticmethod
    def _coerce(raw, field):
        """Turn the configured text into something comparable to the field."""
        if raw is None:
            return raw
        raw = raw.strip() if isinstance(raw, str) else raw
        if field.type in ("integer", "many2one"):
            try:
                return int(raw)
            except (TypeError, ValueError):
                return raw
        if field.type in ("float", "monetary"):
            try:
                return float(raw)
            except (TypeError, ValueError):
                return raw
        if field.type == "boolean":
            return str(raw).strip().lower() in ("1", "true", "yes")
        return raw
