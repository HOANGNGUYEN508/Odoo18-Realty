from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore


class CreateUserWizard(models.TransientModel):
    _name = 'create.user.wizard'
    _description = 'Wizard to Create User with Job Title'

    # Attributes
    name = fields.Char(string='Name', required=True)
    email = fields.Char(string='Email', required=True)
    password = fields.Char(string='Password', required=True)
    citizen_id = fields.Char(string='Citizen ID')

    # Relationship Attributes
    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    province_id = fields.Many2one('res.country.state', string='Province/City')
    district_id = fields.Many2one('district', string='District/Town')
    commune_id = fields.Many2one('commune', string='Commune')
    province_resident_id = fields.Many2one('res.country.state', string='Residence Province/City')
    district_resident_id = fields.Many2one('district', string='Residence District/Town')
    commune_resident_id = fields.Many2one('commune', string='Residence Commune')
    hr_job_id = fields.Many2one(
        'hr.job', 
        string='Job Title', 
        domain="[('active', '=', True)]"
    )

    # Action
    def action_confirm(self):
        """Create a user from wizard data, reset the partner's password, close the wizard, and redirect to the user form."""
        self.ensure_one()
        user_vals = {
            'name': self.name,
            'login': self.email,
            'email': self.email,
            'password': self.password,
            'citizen_id': self.citizen_id,
            'province_id': self.province_id.id,
            'district_id': self.district_id.id,
            'commune_id': self.commune_id.id,
            'province_resident_id': self.province_resident_id.id,
            'district_resident_id': self.district_resident_id.id,
            'commune_resident_id': self.commune_resident_id.id,
            'partner_id': self.partner_id.id,
            'hr_job_id': self.hr_job_id.id if self.hr_job_id else False,
        }

        try:
            user = self.env['res.users'].sudo().create(user_vals)
            self.partner_id.sudo().write({'password': False})
            # Send notification and redirect to the user form
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Successfully',
                    'message': f'User {user.name} was created successfully!',
                    'type': 'success',
                    'sticky': False,
                    'next': {
                        'type': 'ir.actions.act_url',
                        'url': f'/web#id={user.id}&model=res.users&view_type=form',
                        'target': 'self',
                    }
                }
            }
        except Exception as e:
            raise ValidationError(f"Error create uset: {str(e)}")
