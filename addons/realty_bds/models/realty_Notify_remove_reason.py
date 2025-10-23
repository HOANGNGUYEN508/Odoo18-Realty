from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore
from odoo.http import request  # type: ignore
import logging

_logger = logging.getLogger(__name__)


class RemoveReason(models.Model):
    _name = "remove_reason"
    _description = "Canned remove reasons for posts"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"

    # Attributes
    name = fields.Char(string="Name", required=True, tracking=True)
    active = fields.Boolean(string="Active", default=True, tracking=True)

    # Relationship Attributes
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        ondelete="restrict",
        tracking=True,
    )

    # Model Method
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['company_id'] = self.env.company.id
        return super().create(vals_list)

    # Constrain
    _sql_constraints = [
        (
            "remove_reason_unique_name",
            "UNIQUE(name)",
            "This name already exists!",
        ),  # Ensure uniqueness
    ]

    @api.constrains("name")
    def _check_name(self):
        try:
            reserved_words = self.env["policy"].get_reserved_words()
        except KeyError:
            reserved_words = frozenset()
            _logger.warning(
                "The 'policy' model is not available. No reserved words will be checked."
            )
        for record in self:
            clean_name = record.name.strip().lower() if record.name else ""
            if not record.name.strip():  # Prevent empty or spaces-only names
                raise ValidationError(
                    "❌ Error: Name cannot be empty or contain only spaces!")
            if len(record.name) > 100:  # Limit name length
                raise ValidationError(
                    "❌ Error: Name cannot exceed 100 characters!")
            if any(char in record.name for char in
                   r"@#$%&*<>?/|{}[]\!+=;:,"):  # Block special characters
                raise ValidationError(
                    f"❌ Error: Name cannot contain special characters ({r'@#$%&*<>?/|{}[]\!+=;:,'})!")
            match = next((w for w in reserved_words if w in clean_name), None)
            if match:
                raise ValidationError(f"❌ Error: Name contains reserved word: '{match}'!")
