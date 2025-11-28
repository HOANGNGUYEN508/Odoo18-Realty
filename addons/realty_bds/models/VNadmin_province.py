from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore
from odoo.http import request  # type: ignore
import logging

_logger = logging.getLogger(__name__)


class Province(models.Model):
    _inherit = "res.country.state"

    # Relationship Attributes
    region_ids = fields.Many2many("region", string="Region")

    # Constrain
    @api.constrains("name", "region_ids")
    def _check_unique_name_per_region(self):
        """Ensure province name is unique within each region"""
        for record in self:
            if record.region_ids:
                for region in record.region_ids:
                    # Search for other provinces with same name in this region
                    duplicate = self.search([
                        ('id', '!=', record.id),
                        ('name', '=', record.name),
                        ('region_ids', 'in', region.id)
                    ], limit=1)
                    
                    if duplicate:
                        raise ValidationError(f"❌ Error: A province with the name '{record.name}' already exists in region '{region.name}'!")

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
            if not record.name.strip():
                raise ValidationError("❌ Error: Name cannot be empty or contain only spaces!")
            if len(record.name) > 100:
                raise ValidationError("❌ Error: Name cannot exceed 100 characters!")
            if any(char in record.name for char in r"@#$%&*<>?/|{}[]\\!+=;:,"):
                raise ValidationError(f"❌ Error: Name cannot contain special characters ({r'@#$%&*<>?/|{}[]\!+=;:,'})!")
            match = next((w for w in reserved_words if w in clean_name), None)
            if match:
                raise ValidationError(f"❌ Error: Name contains reserved word: '{match}'!")
