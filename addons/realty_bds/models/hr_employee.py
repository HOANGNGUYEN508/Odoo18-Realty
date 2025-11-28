from odoo import models, api, fields  # type: ignore
from odoo.exceptions import UserError, AccessError  # type: ignore
import logging

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    # Action
    def action_terminate_employee(self):
        self.ensure_one()

        group_dict = (
            self.env["permission_tracker"]._get_permission_groups("res.users") or {}
        )
        moderator_group = group_dict.get("moderator_group")
        realty_group = group_dict.get("realty_group")

        if not (
            self.env.user.has_group(moderator_group)
            or self.env.user.has_group(realty_group)
        ):
            raise AccessError(
                "You don't have the necessary permissions to perform this action."
            )

        # Check if trying to terminate own employee record
        current_user_employee_ids = self.env.user.employee_ids.ids
        if self.id in current_user_employee_ids:
            raise UserError("You cannot terminate your own employee record.")

        return {
            "name": "Terminate Employee",
            "type": "ir.actions.act_window",
            "res_model": "hr_employee_wizard",
            "view_mode": "form",
            "views": [
                (
                    self.env.ref(
                        "realty_bds.view_hr_employee_terminate_wizard_form"
                    ).id,
                    "form",
                )
            ],
            "target": "new",
            "context": {
                "default_employee_id": self.id,  # Pass the record ID
                "default_user_id": self.user_id.id,
            },
        }

    def terminate_employee(self):
        """Terminate employees by deleting their records, associated users, and orphaned partners.

        This method handles:
        - Deletion of hr.employee records (current recordset)
        - Deletion of associated res.users records (active or archived)
        - Deletion of orphaned res.partner records (only if no other users remain)
        - Batch operations for performance
        - Works with single or multiple employee records

        """
        if not self:
            return

        ResUsers = self.env["res.users"].sudo()
        ResPartner = self.env["res.partner"].sudo()

        # Collect all user IDs from the employee recordset (including archived)
        user_ids = (
            self.with_context(active_test=False)
            .mapped("user_id")
            .filtered(lambda u: u.exists())
        )

        if not user_ids:
            # No users found, just delete employees
            try:
                self.unlink()
            except Exception as e:
                raise UserError(f"Failed to terminate employees: {str(e)}")
            return

        # Collect partners before deleting users
        partners = user_ids.mapped("partner_id").filtered(lambda p: p.exists())

        # 1) Delete employees first
        try:
            self.unlink()
        except Exception as e:
            raise UserError(f"Failed to terminate employees: {str(e)}")

        # 2) Delete associated users (active and archived)
        try:
            user_ids.unlink()
        except Exception as e:
            _logger.exception("Failed to delete associated users: %s", e)
            # Don't raise here - employees are already deleted
            return

        # 3) Check and delete orphaned partners
        if partners:
            partners_to_delete = ResPartner.browse()
            for partner in partners:
                # Verify partner still exists and has no remaining users
                if partner.exists():
                    remaining_users = ResUsers.with_context(active_test=False).search(
                        [("partner_id", "=", partner.id)], limit=1
                    )
                    if not remaining_users:
                        partners_to_delete |= partner

            if partners_to_delete:
                try:
                    partners_to_delete.unlink()
                except Exception as e:
                    _logger.exception("Failed to delete orphaned partners: %s", e)

        return

    # Model Method
    @api.model_create_multi
    def create(self, vals_list):
        ctx = self.env.context
        if ctx.get("department_assign_mode") and ctx.get("default_department_id"):
            for vals in vals_list:
                vals["department_id"] = ctx["default_department_id"]
        return super().create(vals_list)
