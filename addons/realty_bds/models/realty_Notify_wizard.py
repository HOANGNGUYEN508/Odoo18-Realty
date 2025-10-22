from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError, AccessError  # type: ignore


class NotifyWizard(models.TransientModel):
    _name = "notify_wizard"
    _description = (
        "Generic Wizard use for rejecting posts with reason or removing posts"
    )

    # Attributes
    reason = fields.Text(string="Reason", required=True)
    model_name = fields.Char(
        string="Model Name"
    )  # To track which model we're working with
    record_id = fields.Integer(
        string="Record ID"
    )  # To track which record we're modifying
    action_type = fields.Selection(
        [
            ("reject", "Reject"),
            ("remove", "Remove"),
        ],
        string="Action Type",
    )

    # Selection Attributes
    reject_select = fields.Selection(
        selection="_get_reject_selection",
        string="Reason to Reject",
        help="Choose a predefined reason or 'Other' to enter a custom reason.",
    )
    remove_select = fields.Selection(
        selection="_get_remove_selection",
        string="Reason to Remove",
        help="Choose a predefined reason or 'Other' to enter a custom reason.",
    )

    @api.model
    def _get_reject_selection(self):
        reasons = self.env["reject_reason"].search([])
        return [(reason.name, reason.name) for reason in reasons] + [("other", "Other")]

    @api.model
    def _get_remove_selection(self):
        reasons = self.env["remove_reason"].search([])
        return [(reason.name, reason.name) for reason in reasons] + [("other", "Other")]

    @api.onchange("reject_select")
    def _onchange_reject_select(self):
        if self.reject_select and self.reject_select != "other":
            self.reason = self.reject_select
        elif self.reject_select == "other":
            self.reason = False

    @api.onchange("remove_select")
    def _onchange_remove_select(self):
        if self.remove_select and self.remove_select != "other":
            self.reason = self.remove_select
        elif self.remove_select == "other":
            self.reason = False

    def _get_final_reason(self):
        self.ensure_one()
        if self.action_type == "reject":
            return self.reason if self.reject_select == "other" else self.reject_select
        elif self.action_type == "remove":
            return self.reason if self.remove_select == "other" else self.remove_select
        return False

    # Action
    def action_confirm(self):
        self.ensure_one()

        final_reason = self._get_final_reason()
        if not final_reason:
            raise ValidationError("Reason is required.")

        # Map model names to their respective moderator groups
        model_to_groups = {
            "congratulation": [
                "realty_bds.access_group_mod_congratulation",
                "realty_bds.access_group_realty_congratulation",
            ],
            "guideline": [
                "realty_bds.access_group_mod_guideline",
                "realty_bds.access_group_realty_guideline",
            ],
            "notification": [
                "realty_bds.access_group_mod_notification",
                "realty_bds.access_group_realty_notification_secondary",
            ],
            "urgent_buying": [
                "realty_bds.access_group_mod_urgent_buying",
                "realty_bds.access_group_realty_urgent_buying_secondary",
            ],
        }

        # Get the target model and record
        target_model = self.env[self.model_name]
        record = target_model.browse(self.record_id)

        # Get the required group from mapping
        required_groups = model_to_groups.get(self.model_name)

        if not required_groups:
            raise ValidationError(
                f"No moderator groups defined for model {self.model_name}"
            )

        # Check if user has the required group for this specific model
        has_permission = any(
            self.env.user.has_group(group) for group in required_groups
        )

        if not has_permission:
            group_names = ", ".join(required_groups)
            raise AccessError(
                f"You don't have the necessary permissions to perform this action. Required groups: {group_names}"
            )

        # Check company permission
        if record.company_id != self.env.user.company_id and record.company_id.id != 1:
            raise AccessError("You can only reject posts from your own company.")

        # Perform action based on action_type
        if self.action_type == "reject":
            # Check edit counter
            value = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("realty_bds.editcounter", default="3")
            )

            try:
                default_counter = int(value)
            except (TypeError, ValueError):
                default_counter = 3

            edit_counter = record.edit_counter

            if record.edit_counter != -1:
                edit_counter -= 1
            else:
                edit_counter = default_counter

            record.write(
                {
                    "approval": "rejected",
                    "edit_counter": edit_counter,
                    "moderator_id": self.env.user.id,
                    "moderated_at": fields.Datetime.now(),
                    "reason": final_reason,
                }
            )
        elif self.action_type == "remove":
            record.write(
                {
                    "approval": "removed",
                    "moderator_id": self.env.user.id,
                    "moderated_at": fields.Datetime.now(),
                    "reason": final_reason,
                }
            )
        else:
            raise ValidationError("Invalid action type.")

        return {"type": "ir.actions.act_window_close"}
