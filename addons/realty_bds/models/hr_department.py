from odoo import models, fields, api  # type: ignore


class HrDepartment(models.Model):
    _inherit = "hr.department"

    # Relationship Attributes
    employee_ids = fields.One2many("hr.employee", "department_id", string="Employees")

    # Action
    def action_open_assign_employee_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Assign Employees",
            "res_model": "assign.employee.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "active_id": self.id,
            },
        }
