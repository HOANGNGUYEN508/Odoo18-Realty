from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError, AccessError, UserError  # type: ignore


class HrEmployeeWizard(models.TransientModel):
    _name = "hr_employee_wizard"
    _description = "Generic Wizard use for removing comment with reason"

    # Relationship Attributes
    employee_id = fields.Many2one("hr.employee", string="Employee", readonly=True)
    user_id = fields.Many2one("res.users", string="User", readonly=True)

    # Action
    def action_confirm(self):
        self.ensure_one()
        self.employee_id.terminate_employee()
        return {"type": "ir.actions.act_window_close"}
