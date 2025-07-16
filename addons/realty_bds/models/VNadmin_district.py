from odoo import models, fields, api # type: ignore
from odoo.exceptions import ValidationError # type: ignore
from odoo.http import request # type: ignore
import logging
_logger = logging.getLogger(__name__)

class District(models.Model):
    _inherit = 'district'
    
    # Constrain
    @api.constrains('name')
    def _check_name(self):
        reserved_words = []
        try:
            reserved_words = request.env['policy'].sudo().search([]).mapped('name')
        except KeyError:
            _logger.warning("The 'policy' model is not available. No reserved words will be checked.")
        # Normalize the reserved words to lowercase and remove any extra spaces
        reserved_words = set(word.strip().lower() for word in reserved_words)
        # Validate each record's name
        for record in self:
            clean_name = record.name.strip().lower()
            # Check for various validation errors
            if not record.name.strip():  # Prevent empty or spaces-only names
                raise ValidationError("❌ Error: Name cannot be empty or contain only spaces!")
            if len(record.name) > 100:  # Limit name length
                raise ValidationError("❌ Error: Name cannot exceed 100 characters!")
            # Block special characters
            if any(char in record.name for char in r"@#$%^&*()<>?/|{}[]\\!+-=`;:.,~"):
                raise ValidationError("❌ Error: Name cannot contain special characters!")
            if clean_name in reserved_words:  # Prevent reserved words
                raise ValidationError(f"❌ Error: Name '{record.name}' is not allowed!")