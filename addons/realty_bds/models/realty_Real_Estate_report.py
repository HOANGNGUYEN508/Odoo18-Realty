from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore
from odoo.http import request  # type: ignore
import re
import logging

_logger = logging.getLogger(__name__)


class ProductReport(models.Model):
    _name = "product_report"
    _description = "Real Estate Report"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"

    # Attributes
    name = fields.Char(string="Name", required=True, tracking=True)
    customer = fields.Char(string="Customer", required=True, tracking=True)
    citizen_id = fields.Char(string="Citizen ID", required=True, tracking=True)
    phone = fields.Char(string="Phone", required=True, tracking=True)
    email = fields.Char(string="Email", required=True, tracking=True)
    active = fields.Boolean(string="Active", default=True, tracking=True)
    opinions = fields.Text(string="Initial Opinions",
                           required=True,
                           tracking=True)
    other_reason = fields.Text(
        string="Other Reason",
        help="Enter your reason if you selected 'Other'.",
        tracking=True,
    )
    other_owner_feedback = fields.Text(
        string="Other Owner Feedback",
        help="Enter your owner feedback if you selected 'Other'.",
        tracking=True,
    )
    other_client_feedback = fields.Text(
        string="Other Client Feedback",
        help="Enter your client feedback if you selected 'Other'.",
        tracking=True,
    )
    approval = fields.Selection(
        [
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Approval",
        default="pending",
        tracking=True,
    )

    # Relationship Attributes
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    product_id = fields.Many2one(
        "product.template",
        string="Product",
        required=True,
        ondelete="cascade",
        tracking=True,
    )
    img_ids = fields.Many2many(
        "ir.attachment",
        required=True,
        string="Images",
        domain="[('mimetype', 'like', 'image/%')]",
    )

    # Compute Attributes
    reason = fields.Text(
        compute="_compute_reason",
        store=True,
        string="True Reason",
        help="Stores the final reason (predefined or custom text).",
        tracking=True,
    )
    owner_feedback = fields.Text(
        compute="_compute_owner_feedback",
        store=True,
        string="True Owner Feedback",
        help="Stores the final owner feedback (predefined or custom text).",
        tracking=True,
    )
    client_feedback = fields.Text(
        compute="_compute_client_feedback",
        store=True,
        string="True Client Feedback",
        help="Stores the final client feedback (predefined or custom text).",
        tracking=True,
    )

    @api.depends("reason_selection", "other_reason")
    def _compute_reason(self):
        for report in self:
            if report.reason_selection == "other":
                report.reason = report.other_reason  # Store custom text
            elif report.reason_selection:
                report.reason = report.reason_selection  # Store predefined reason
            else:
                report.reason = False

    @api.depends("owner_feedback_selection", "other_owner_feedback")
    def _compute_owner_feedback(self):
        for report in self:
            if report.owner_feedback_selection == "other":
                report.owner_feedback = report.other_owner_feedback  # Store custom text
            elif report.owner_feedback_selection:
                report.owner_feedback = (report.owner_feedback_selection
                                         )  # Store predefined reason
            else:
                report.owner_feedback = False

    @api.depends("client_feedback_selection", "other_client_feedback")
    def _compute_client_feedback(self):
        for report in self:
            if report.client_feedback_selection == "other":
                report.client_feedback = (report.other_client_feedback
                                          )  # Store custom text
            elif report.client_feedback_selection:
                report.client_feedback = (report.client_feedback_selection
                                          )  # Store predefined reason
            else:
                report.client_feedback = False

    # Selection Attributes
    reason_selection = fields.Selection(
        selection="_get_reason_selection",
        string="Reason to Buy",
        help="Choose a predefined reason or 'Other' to enter a custom reason.",
    )
    client_feedback_selection = fields.Selection(
        selection="_get_client_feedback_selection",
        string="Client Feedback",
        help=
        "Choose a predefined client feedback or 'Other' to enter a custom client feedback.",
    )
    owner_feedback_selection = fields.Selection(
        selection="_get_owner_feedback_selection",
        string="Owner Feedback",
        help=
        "Choose a predefined owner feedback or 'Other' to enter a custom owner feedback.",
    )

    def _get_reason_selection(self):
        reasons = self.env["reasons_buy"].search([])
        return [(reason.name, reason.name)
                for reason in reasons] + [("other", "Other")]

    def _get_owner_feedback_selection(self):
        owner_feedbacks = self.env["owner_feedback"].search([])
        return [(owner_feedback.name, owner_feedback.name)
                for owner_feedback in owner_feedbacks] + [("other", "Other")]

    def _get_client_feedback_selection(self):
        client_feedbacks = self.env["client_feedback"].search([])
        return [(client_feedback.name, client_feedback.name)
                for client_feedback in client_feedbacks] + [("other", "Other")]

    # Model Method
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['company_id'] = self.env.company.id
        return super().create(vals_list)
    
    def unlink(self):
        # collect attachments before deleting (so we know which records were involved)
        attachments = self.mapped('img_ids')
        rec_ids = self.ids[:]
        model_name = self._name

        # delete the records (this removes the M2M relation rows)
        res = super().unlink()

        # clear res_model/res_id for attachments that pointed to those records
        attachments_to_clear = attachments.filtered(
            lambda a: a.res_model == model_name and a.res_id in rec_ids
        )
        if attachments_to_clear:
            # use sudo() if your users may not have rights to edit ir.attachment
            attachments_to_clear.sudo().write({'res_model': False, 'res_id': False})

        return res

    # Constrain
    _sql_constraints = [
        (
            "unique_name",
            "UNIQUE(name)",
            "This name already exists!",
        ),  # Ensure uniqueness
    ]

    @api.constrains("phone")
    def _check_phone(self):
        pattern = re.compile(r"^\d{9,12}$")
        for rec in self:
            if not pattern.match(rec.phone or ""):
                raise ValidationError(
                    "❌ Error: Phone must be 9-12 digits, numbers only.")

    @api.constrains("citizen_id")
    def _check_citizen_id(self):
        pattern = re.compile(r"^\d{9,12}$")
        for rec in self:
            if not pattern.match(rec.citizen_id or ""):
                raise ValidationError(
                    "❌ Error: Citizen ID must be 9-12 digits, numbers only.")

    @api.constrains("email")
    def _check_email(self):
        # very simple RFC-style check
        pattern = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
        for rec in self:
            if not pattern.match(rec.email or ""):
                raise ValidationError(
                    "❌ Error: Please enter a valid email address.")

    @api.constrains(
        "name",
        "customer",
        "opinions",
        "reason",
        "owner_feedback",
        "client_feedback",
    )
    def _check_text_fields(self):
        try:
            reserved_words = self.env["policy"].get_reserved_words()
        except KeyError:
            reserved_words = frozenset()
            _logger.warning(
                "The 'policy' model is not available. No reserved words will be checked."
            )

        # Define per-field requirements
        specs = {
            "name": {
                "max_len": 100,
                "allow_empty": False
            },
            "customer": {
                "max_len": 100,
                "allow_empty": False
            },
            "opinions": {
                "max_len": 500,
                "allow_empty": False
            },
            "reason": {
                "max_len": 300,
                "allow_empty": False
            },
            "owner_feedback": {
                "max_len": 300,
                "allow_empty": False
            },
            "client_feedback": {
                "max_len": 300,
                "allow_empty": False
            },
        }
        special_chars = set(r"@#$%&*<>?/|{}[]\!+=;:,")

        for rec in self:
            for field_name, rules in specs.items():
                val = getattr(rec, field_name) or ""
                text = val.strip().lower()
                # Empty check
                if not text and not rules["allow_empty"]:
                    raise ValidationError(
                        f"❌ Error: {field_name.replace('_',' ').title()} cannot be empty."
                    )
                # Length check
                if len(text) > rules["max_len"]:
                    raise ValidationError(
                        f"❌ Error: {field_name.replace('_',' ').title()} cannot exceed {rules['max_len']} characters.")
                # Special-character check
                if any(ch in special_chars for ch in text):
                    raise ValidationError(
                        f"❌ Error: {field_name.replace('_',' ').title()} cannot contain special characters ({r'@#$%&*<>?/|{}[]\!+=;:,'}).")
                # Reserved-word check
                match = next((w for w in reserved_words if w in text), None)
                if match:
                    raise ValidationError(
                        f"❌ Error: {field_name.replace('_',' ').title()} contains reserved word: '{match}'!")
