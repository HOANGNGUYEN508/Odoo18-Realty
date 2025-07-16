from odoo import models, fields, api # type: ignore
from odoo.exceptions import ValidationError # type: ignore
from odoo.http import request # type: ignore

class District(models.Model):
    _name = 'district'
    _description = 'District'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'  # Sort field "name" alphabetically
    
		# Attributes
    active = fields.Boolean(string="Active", default=True, tracking=True)
    name = fields.Char(string="District", 
                       tracking=True, 
                       required=True)
    
		# Relationship Attributes
    province_id = fields.Many2one('res.country.state', 
                                  string="Province/City", 
                                  required=True, 
                                  domain="[('country_id.code', '=', 'VN')]", 
                                  tracking=True)
    commune_ids = fields.One2many('commune', 
                                  'district_id', 
                                  string="Commune List", 
                                  tracking=True)

    #Constrain
    _sql_constraints = [
        ('unique_name', 'UNIQUE(name,province_id)', 'This name already exists!'),  # Ensure uniqueness
    ]
    