from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore
from odoo.http import request  # type: ignore
import re
import logging

_logger = logging.getLogger(__name__)


class Tag(models.Model):
    _name = "tag"
    _description = "Tag List"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"

    # Attributes
    name = fields.Char(string="Name", required=True, tracking=True)
    active = fields.Boolean(string="Active", default=True, required=True)

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
            "tag_unique_name",
            "UNIQUE(name)",
            "This name already exists!",
        ),  # Ensure uniqueness
    ]
    

    @api.constrains("name")
    def _check_tag_name(self):
        # Allow only letters, numbers, and underscores and must start with #
        tag_pattern = r"^#[a-zA-Z0-9_]{1,29}$"
        try:
            reserved_words = self.env["policy"].get_reserved_words()
        except KeyError:
            reserved_words = frozenset()
            _logger.warning(
                "The 'policy' model is not available. No reserved words will be checked."
            )
            
        for record in self:
            clean_name = record.name.strip().lower() if record.name else ""
            if " " in record.name:  # Prevent spaces between multiple tags
                raise ValidationError(
                    "❌ Error: Only one tag is allowed, no spaces permitted!")
            if not record.name.strip():  # Prevent empty or spaces-only names
                raise ValidationError(
                    "❌ Error: Name cannot be empty or contain only whitespace.!"
                )
            if len(record.name) > 30:  # Limit name length
                raise ValidationError(
                    "❌ Error: Name must not exceed 30 characters!")
            if any(char in record.name
                   for char in r"@$%^&*()<>?/|{}[]\\!+-=`;:.,~"
                   ):  # Block special characters
                raise ValidationError(
                    f"❌ Error: Tag must not contain special characters ({r'@$%^&*()<>?/|{}[]\\!+-=`;:.,~'})!")
            if record.name.count('#') != 1:
                raise ValidationError("❌ Error: Only a single '#' allow at the start!")	
            match = next((w for w in reserved_words if w in clean_name[1:]), None)
            if match:
                raise ValidationError(f"❌ Error: Tag contains reserved word: '{match}'!")
            if not re.match(
                    tag_pattern, record.name
            ):  # Enforce valid format: Must start with # and contain only letters, numbers, or _
                raise ValidationError(
                    "❌ Error: Tag must start with # and contain only letters, numbers, or underscores (_)!"
                )
