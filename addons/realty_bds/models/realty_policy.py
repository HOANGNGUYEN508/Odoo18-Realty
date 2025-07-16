from odoo import models, fields, api # type: ignore
from odoo.exceptions import ValidationError # type: ignore

class Policy(models.Model):
    _name = 'policy'
    _description = 'Policy List'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    
		# Attributes
    name = fields.Char(string="Name", required=True, help="Start typing to see suggestions for existing items", tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    
		# Relationship Attributes
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True, ondelete='restrict', tracking=True)
    
    # Constrains
    _sql_constraints = [
        ('unique_name', 'UNIQUE(name)', 'This name already exists!'),  # Ensure uniqueness
    ]

    @api.constrains('name')
    def _check_name(self):
        for record in self:
            if not record.name.strip():  # Prevent empty or spaces-only names
                raise ValidationError("❌ Error: Name cannot be empty or contain only spaces!")
            if len(record.name) > 100:  # Limit name length
                raise ValidationError("❌ Error: Name cannot exceed 100 characters!")
            if any(char in record.name for char in r"@#$%&*<>?/|{}[]\\!+=;:,"):  # Block special characters
                raise ValidationError("❌ Error: Name cannot contain special characters!")
            if " " in record.name:
                raise ValidationError("❌ Error: Don't contain spaces!")
