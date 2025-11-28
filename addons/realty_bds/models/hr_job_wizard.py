from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError, AccessError, UserError  # type: ignore


class HrjobWizard(models.TransientModel):
    _name = "hr_job_wizard"
    _description = "Wizard use for setting default job position"

    # Relationship Attributes
    default_job_id = fields.Many2one(
        'hr.job', 
        string='Default',
        help="Select the default job position for new users",
    )
    
    company_selection = fields.Selection(
        selection="_get_company_selection",
        string="Company",
        help="Company for which to set the default job position",
    )

    # Selection Attributes
    job_selection = fields.Selection(
        selection="_get_job_selection",
        string="Job Position",
        help="Choose a predefined reason or 'Other' to enter a custom reason.",
    )

    @api.model
    def _get_job_selection(self):
        # Get the external ID reference for the restricted job
        try:
            restricted_job = self.env.ref('realty_bds.realty_superUser')
            restricted_job_id = restricted_job.id
        except ValueError:
            # If the external ID doesn't exist, set to None
            restricted_job_id = None
        
        # Search for active jobs excluding the restricted one
        domain = [('active', '=', True)]
        if restricted_job_id:
            domain.append(('id', '!=', restricted_job_id))
        
        jobs = self.env["hr.job"].search(domain)
        return [(str(job.id), job.name) for job in jobs]
    
    @api.model
    def _get_company_selection(self):
        # Check if user has the realty_superUser job
        try:
            restricted_job = self.env.ref('realty_bds.realty_superUser')
            user_has_super_job = self.env.user.employee_id.job_id == restricted_job
        except ValueError:
            user_has_super_job = False
        
        # If user has super job, return all companies; otherwise only current company
        if user_has_super_job:
            companies = self.env['res.company'].search([])
        else:
            companies = self.env.company
        
        return [(str(company.id), company.name) for company in companies]

    @api.model
    def default_get(self, fields_list):
        """Load the current default job from system parameters"""
        res = super(HrjobWizard, self).default_get(fields_list)
        if 'default_job_id' in fields_list:
            params = self.env['ir.config_parameter'].sudo()
            job_id = params.get_param(f'realty_bds.default_job_id_{self.env.company.id}', default=False)
            if job_id:
                res['default_job_id'] = int(job_id)
        return res
    
    # Action
    def action_confirm(self):
        self.ensure_one()

        group_dict = self.env["permission_tracker"]._get_permission_groups("res.users") or {}
        moderator_group = group_dict.get("moderator_group")
        realty_group = group_dict.get("realty_group")
        if not (self.env.user.has_group(moderator_group) or self.env.user.has_group(realty_group)):
            raise AccessError("You don't have the necessary permissions to perform this action.")

        # Check if trying to set the restricted job
        if self.job_select:
            try:
                restricted_job = self.env.ref('realty_bds.realty_superUser')
                if int(self.job_select) == restricted_job.id:
                    raise UserError("The 'Realty Super User' job position cannot be set as the default job.")
            except ValueError:
                # External ID doesn't exist, continue normally
                pass
            
            # Save the default job position to system parameters
            self.env['ir.config_parameter'].sudo().set_param(
                f'realty_bds.default_job_id_{self.company_selection}', 
                self.job_select
            )
            
        return {"type": "ir.actions.act_window_close"}