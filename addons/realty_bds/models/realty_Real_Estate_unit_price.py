from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore
from odoo.http import request  # type: ignore
import math
import logging

_logger = logging.getLogger(__name__)


class UnitPrice(models.Model):
    _name = "unit_price"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Unit Price List"

    # Attributes
    name = fields.Char(string="Name", required=True, tracking=True)
    multiplier = fields.Float(string="Multiplier",
                              required=True,
                              tracking=True)
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
            "unit_price_unique_name",
            "UNIQUE(name)",
            "This name already exists!",
        ),  # Ensure uniqueness
    ]

    @api.constrains("name")
    def _check_name(self):
        reserved_words = []
        try:
            reserved_words = request.env["policy"].sudo().search(
                []).mapped("name")
        except KeyError:
            _logger.warning(
                "The 'policy' model is not available. No reserved words will be checked."
            )
        # Normalize the reserved words to lowercase and remove any extra spaces
        reserved_words = set(word.strip().lower() for word in reserved_words)
        # Validate each record's name
        for record in self:
            clean_name = record.name.strip().lower()
            # Check for various validation errors
            if not record.name.strip():  # Prevent empty or spaces-only names
                raise ValidationError(
                    "❌ Error: Name cannot be empty or contain only spaces!")
            if len(record.name) > 100:  # Limit name length
                raise ValidationError(
                    "❌ Error: Name cannot exceed 100 characters!")
            # Block special characters
            if any(char in record.name
                   for char in r"@#$%^&*()<>?/|{}[]\\!+-=`;:.,~"):
                raise ValidationError(
                    "❌ Error: Name cannot contain special characters!")
            if clean_name in reserved_words:  # Prevent reserved words
                raise ValidationError(
                    f"❌ Error: Name '{record.name}' is not allowed!")

    @api.constrains("multiplier")
    def _check_power_of_10(self):
        for record in self:
            if record.multiplier <= 0:
                raise ValidationError(
                    "❌ Error: Multiplier must be greater than 0!")
            else:
                if not math.log10(record.multiplier).is_integer():
                    raise ValidationError(
                        "❌ Lỗi: Multiplier must be a power of 10!")
