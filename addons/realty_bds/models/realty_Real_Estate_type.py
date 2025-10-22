from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore
from odoo.http import request  # type: ignore


class Type(models.Model):
    _name = "type"
    _description = "Real Estate Type"
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
            "type_unique_name",
            "UNIQUE(name)",
            "This name already exists!",
        ),  # Ensure uniqueness
    ]

    @api.constrains("name")
    def _check_name(self):
        # Fetch reserved words dynamically from the policy model
        reserved_words = request.env["policy"].sudo().search([]).mapped("name")
        reserved_words = set(word.strip().lower()
                             for word in reserved_words)  # Normalize
        for record in self:
            # Convert to lowercase to check correctly
            clean_name = record.name.strip().lower()
            if not record.name.strip():  # Prevent empty or spaces-only names
                raise ValidationError(
                    "❌ Error: Name cannot be empty or contain only spaces!")
            if len(record.name) > 100:  # Limit name length
                raise ValidationError(
                    "❌ Error: Name cannot exceed 100 characters!")
            if any(char in record.name for char in
                   r"@#$%&*<>?/|{}[]\\!+=;:,"):  # Block special characters
                raise ValidationError(
                    "❌ Error: Name cannot contain special characters!")
            if clean_name in reserved_words:  # Prevent reserved words
                raise ValidationError(
                    f"❌ Error: Name '{record.name}' is not allowed!")
