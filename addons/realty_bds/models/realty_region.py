from odoo import models, fields, api # type: ignore
from odoo.exceptions import ValidationError # type: ignore
from odoo.http import request # type: ignore

class Region(models.Model):
    _name = 'region'
    _description = 'Region List'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'
    
    # Attributes
    name = fields.Char(string="Name", tracking=True, required=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    
		# Relationship Attributes
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True, ondelete='restrict', tracking=True)
    province_ids = fields.Many2many('res.country.state', string="Province List", tracking=True)

    # Constrain
    _sql_constraints = [
        ('unique_name', 'UNIQUE(name)', 'This name already exists!'),  # Ensure uniqueness
    ]
    
    @api.constrains('name')
    def _check_name(self):
        # Fetch reserved words dynamically from the policy model
        reserved_words = request.env['policy'].sudo().search([]).mapped('name')
        reserved_words = set(word.strip().lower() for word in reserved_words)  # Normalize        
        for record in self:
            clean_name = record.name.strip().lower()  # Convert to lowercase to check correctly
            if not record.name.strip():  # Prevent empty or spaces-only names
                raise ValidationError("❌ Error: Name cannot be empty or contain only spaces!")
            if len(record.name) > 100:  # Limit name length
                raise ValidationError("❌ Error: Name cannot exceed 100 characters!")
            if any(char in record.name for char in r"@#$%&*<>?/|{}[]\\!+=;:,"):  # Block special characters
                raise ValidationError("❌ Error: Name cannot contain special characters!")
            if clean_name in reserved_words:  # Prevent reserved words
                raise ValidationError(f"❌ Error: Name '{record.name}' is not allowed!")