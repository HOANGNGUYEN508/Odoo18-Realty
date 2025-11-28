from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError, AccessError, UserError  # type: ignore


class UserEvaluationWizard(models.TransientModel):
    _name = "user_evaluation_wizard"
    _description = "Generic Wizard use for removing user evaluation with reason"

    # Attributes
    reason = fields.Text(string="Reason", required=True)
    res_model = fields.Char(string="Model Name")
    res_id = fields.Integer(string="Record ID")
    note = fields.Text(string="Moderator Notes")
    action_type = fields.Selection(
        [
            ("reject", "Reject"),
            ("note", "Take Note"),
        ],
        string="Action Type",
    )

    # Selection Attributes
    reject_select = fields.Selection(
        selection="_get_reject_selection",
        string="Reason to Reject",
        help="Choose a predefined reason or 'Other' to enter a custom reason.",
    )

    @api.model
    def _get_reject_selection(self):
        reasons = self.env["reject_reason"].search([("for_type", "=", "user_evaluation"),
                                                    ("active", "=", True)])

        return [(reason.name, reason.name)
                for reason in reasons] + [("other", "Other")]

    @api.onchange("reject_select")
    def _onchange_reject_select(self):
        if self.reject_select and self.reject_select != "other":
            self.reason = self.reject_select

    def _get_final_reason(self):
        self.ensure_one()
        return self.reason if self.reject_select == "other" else self.reject_select

    # Action
    def action_confirm(self):
        self.ensure_one()

        group_dict = self.env["permission_tracker"]._get_permission_groups("res.users") or {}
        moderator_group = group_dict.get("moderator_group")
        realty_group = group_dict.get("realty_group")
        if not (self.env.user.has_group(moderator_group) or self.env.user.has_group(realty_group)):
            raise AccessError("You don't have the necessary permissions to perform this action.")

        evaluation = self.env["user_evaluation"].sudo().browse(self.res_id).exists()
        if not evaluation:
            raise UserError("The record no longer exists (deleted by another user). Please exit the form.")

        if self.action_type == "reject":
            final_reason = self._get_final_reason()
            if not final_reason:
                raise ValidationError("Reason is required.")
            vals = {
                "state": "rejected",
                "moderator_id": self.env.user,
                "moderated_on": fields.Datetime.now(),
                "reason": final_reason,
            }
            evaluation.write(vals)
            if evaluation.user_id:
                evaluation.user_id.write({"active": False})
                employee = self.env["hr.employee"].sudo().browse(evaluation.user_id.id)
                if employee.exists(): employee.write({"active": False})

        elif self.action_type == "note":
            if not self.note:
                raise ValidationError("Notes are required.")
            evaluation.write({"note": self.note})

        return {"type": "ir.actions.act_window_close"}