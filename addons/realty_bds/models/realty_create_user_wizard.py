from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore


class CreateUserWizard(models.TransientModel):
    _name = "create.user.wizard"
    _description = "Wizard to Create User with Job Title"

    # Attributes
    name = fields.Char(string="Name", required=True)
    email = fields.Char(string="Email", required=True)
    password = fields.Char(string="Password", required=True)
    job_selection = fields.Selection(
        selection="_get_job_selection",
        string="Job Position",
        help="Choose a predefined reason or 'Other' to enter a custom reason.",
    )

    # Relationship Attributes
    partner_id = fields.Many2one("res.partner", string="Partner", required=True)
    hr_job_id = fields.Many2one(
        "hr.job",
        string="Default",
        domain="[('active', '=', True)]",
        default=lambda self: self._get_default_job(),
    )

    def _get_default_job(self):
        """Get default job from system parameter (by name)"""
        default_job_id = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(f"realty_bds.default_job_id_{self.env.user.company_id.id}", default=False)
        )

        if default_job_id:
            job = self.env["hr.job"].browse(default_job_id)

            if job:
                return job.id

        return False
    
    @api.model
    def _get_job_selection(self):
        # Get the external ID reference for the restricted job
        try:
            restricted_job = self.env.ref('realty_bds.realty_superUser')
            restricted_job_id = restricted_job.id
        except ValueError:
            # If the external ID doesn't exist, set to None
            restricted_job_id = None
        
        # Check if current user has the restricted job
        user_has_restricted_job = False
        if restricted_job_id and self.env.user.employee_id.job_id:
            user_has_restricted_job = self.env.user.employee_id.job_id.id == restricted_job_id
        
        # Search for active jobs excluding the restricted one
        domain = [('active', '=', True)]
        if restricted_job_id:
            domain.append(('id', '!=', restricted_job_id))
        
        # If user doesn't have restricted job, filter by their company
        if not user_has_restricted_job:
            user_company_id = self.env.user.company_id.id
            domain.append(('company_id', '=', user_company_id))
        
        jobs = self.env["hr.job"].search(domain)
        return [(str(job.id), job.name) for job in jobs]
    
    # Action
    def action_confirm(self):
        """Create a user from wizard data, close the wizard, and redirect to the user form."""
        self.ensure_one()
        if not self.email:
            raise ValidationError("Email is required!")
        if not self.password:
            raise ValidationError("Password is required!")
        
        # Determine which job to use
        job_id = False
        if self.job_selection:
            # If job_selection is selected, use it
            job_id = int(self.job_selection)
        else:
            # If no selection, try to get default job
            default_job_id = self._get_default_job()
            if default_job_id:
                job_id = default_job_id

        user_vals = {
            "name": self.name,
            "login": self.email,
            "email": self.email,
            "password": self.password,
            "partner_id": self.partner_id.id,
        }

        if job_id:
            user_vals["hr_job_id"] = job_id

        try:
            user = self.env["res.users"].sudo().create(user_vals)
            # Send notification and redirect to the user form
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Successfully",
                    "message": f"User {user.name} was created successfully!",
                    "type": "success",
                    "sticky": False,
                    "next": {
                        "type": "ir.actions.act_url",
                        "url": f"/web#id={user.id}&model=res.users&view_type=form",
                        "target": "self",
                    },
                },
            }
        except Exception as e:
            raise ValidationError(f"Error create user: {str(e)}")
