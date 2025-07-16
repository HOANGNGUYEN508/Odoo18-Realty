from odoo import models, fields, api # type: ignore
from odoo.exceptions import ValidationError, AccessError  # type: ignore

class ResCompany(models.Model):
    _inherit = 'res.company'
    
		# Relationship Attributes
    province_id = fields.Many2one('res.country.state', string="Province/City", ondelete='restrict')
    district_id = fields.Many2one(
        'district', 
        string="District/Town", 
        domain="[('province_id', '=', province_id)]", 
        ondelete='restrict'
    )
    commune_id = fields.Many2one(
        'commune', 
        string="Commune", 
        domain="[('district_id', '=', district_id)]", 
      	ondelete='restrict'
    )
    
    # Constrain
    @api.constrains('province_id', 'district_id', 'commune_id')
    def _check_location_consistency1(self):
        for record in self:
            if record.district_id and record.district_id.province_id != record.province_id:
                raise ValidationError("❌ District does not match the selected province!")
            if record.commune_id and record.commune_id.district_id != record.district_id:
                raise ValidationError("❌ Commune does not match the selected district!")
            
    # Onchange
    @api.onchange('province_id')
    def _onchange_province_id(self):
        if self.province_id:
            if self.district_id and self.district_id.province_id != self.province_id:
                self.district_id = False
            if self.commune_id:
                self.commune_id = False
            return {'domain': {'district_id': [('province_id', '=', self.province_id.id)]}}
        else:
            self.district_id = False
            self.commune_id = False
        return {'domain': {'district_id': []}}

    @api.onchange('district_id')
    def _onchange_district_id(self):
        if self.district_id:
            if self.commune_id and self.commune_id.district_id != self.district_id:
                self.commune_id = False
            return {'domain': {'commune_id': [('district_id', '=', self.district_id.id)]}}
        else:
            self.commune_id = False
        return {'domain': {'commune_id': []}}