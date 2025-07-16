from odoo import models, fields, api # type: ignore
from odoo.exceptions import ValidationError # type: ignore
from odoo.http import request # type: ignore
import re

class Tag(models.Model):
    _name = 'tag'
    _description = 'Tag List'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

		# Attributes
    name = fields.Char(string="Name", required=True, help="Start typing to see suggestions for existing items", tracking=True)
    active = fields.Boolean(string='Active', default=True, required=True)
    
		# Relationship Attributes
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True, ondelete='restrict', tracking=True)

    # Constrain
    _sql_constraints = [
        ('unique_name', 'UNIQUE(name)', 'This name already exists!'),  # Ensure uniqueness
    ]

    @api.constrains('name')
    def _check_tag_name(self):         
        # Must start with # and allow only letters, numbers, and underscores    
        tag_pattern = r"^#[a-zA-Z0-9_]{1,29}$"  
        # Fetch reserved words dynamically from the policy model
        reserved_words = request.env['policy'].sudo().search([]).mapped('name')  
        reserved_words = set(word.strip().lower() for word in reserved_words)  # Normalize
        for record in self:
            clean_name = record.name.strip().lower()  # Convert to lowercase to check correctly
            if " " in record.name: # Prevent spaces between multiple tags
                raise ValidationError("❌ Error: Only one tag is allowed, no spaces permitted!")
            if not record.name.strip():  # Prevent empty or spaces-only names
                raise ValidationError("❌ Error: Name cannot be empty or contain only whitespace.!")
            if len(record.name) > 30:  # Limit name length
                raise ValidationError("❌ Error: Name must not exceed 30 characters!")
            if any(char in record.name for char in r"@$%^&*()<>?/|{}[]\\!+-=`;:.,~"):  # Block special characters
                raise ValidationError("❌ Error: Name must not contain special characters!")
            if clean_name in reserved_words:  # Prevent reserved words
                raise ValidationError(f"❌ Error: The name '{record.name}' is not allowed!")
            if not re.match(tag_pattern, record.name): # Enforce valid format: Must start with # and contain only letters, numbers, or _
                raise ValidationError("❌ Error: Tag must start with '#' and contain only letters, numbers, or underscores (_)!")
            if record.name.count("#") > 1: # Prevent multiple hashtags in one tag (e.g., "#love#happy")
                raise ValidationError("❌ Error: Only one tag starting with '#' is allowed!")