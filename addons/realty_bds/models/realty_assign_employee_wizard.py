from odoo import models, fields, api  # type: ignore


class AssignEmployeeWizard(models.TransientModel):
    _name = "assign.employee.wizard"
    _description = "Assign Employees to Department Wizard"

    # Relationship Attributes
    department_id = fields.Many2one(
        "hr.department",
        string="Department",
        required=True,
        default=lambda self: self.env.context.get("active_id"),
    )
    employee_ids = fields.Many2many(
        "hr.employee", string="Employees", domain=[("department_id", "=", False)]
    )

    # Action
    def action_assign_employees(self):
        self.ensure_one()
        if self.employee_ids:
            self.employee_ids.write({"department_id": self.department_id.id})
        return {"type": "ir.actions.act_window_close"}
