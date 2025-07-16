from odoo import models, api, fields # type: ignore

class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    
		# Model Method
    @api.model_create_multi
    def create(self, vals_list):
        ctx = self.env.context
        if ctx.get('department_assign_mode') and ctx.get('default_department_id'):
            for vals in vals_list:
                vals['department_id'] = ctx['default_department_id']
        return super().create(vals_list)
