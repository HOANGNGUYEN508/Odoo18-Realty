from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError, AccessError, UserError  # type: ignore


class NotifyWizard(models.TransientModel):
    _name = "notify_wizard"
    _description = "Generic Wizard use for rejecting posts with reason or removing posts"

    # Attributes
    reason = fields.Text(string="Reason", required=True)
    res_model = fields.Char(string="Model Name")
    res_id = fields.Integer(string="Record ID")
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
        reasons = self.env["reject_reason"].search([("active", "=", True)])
        return [(reason.name, reason.name)
                for reason in reasons] + [("other", "Other")]

    @api.model
    def _get_remove_selection(self):
        reasons = self.env["remove_reason"].search([("for_type", "=", "post"),
                                                    ("active", "=", True)])

        return [(reason.name, reason.name)
                for reason in reasons] + [("other", "Other")]

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

        group_dict = self.env["permission_tracker"]._get_permission_groups(self.res_model) or {}

        moderator_group = group_dict.get("moderator_group")
        realty_group = group_dict.get("realty_group")
        if not (self.env.user.has_group(moderator_group)
                or self.env.user.has_group(realty_group)):
            raise AccessError(
                f"You don't have the necessary permissions to perform this action."
            )

        # Get the target model and record
        target_model = self.env[self.res_model]
        record = target_model.browse(self.res_id)

        # Check company permission
        if record.company_id != self.env.user.company_id and record.company_id.id != 1:
            raise AccessError("You can only reject posts from your own company.")

        # Perform action based on action_type
        if self.action_type == "reject":
            # Check edit counter
            value = (self.env["ir.config_parameter"].sudo().get_param("realty_bds.editcounter", default="3"))

            try:
                default_counter = int(value)
            except (TypeError, ValueError):
                default_counter = 3

            edit_counter = record.edit_counter

            if record.edit_counter != -1:
                edit_counter -= 1
            else:
                edit_counter = default_counter

            record.write({
                "approval": "rejected",
                "edit_counter": edit_counter,
                "moderator_id": self.env.user.id,
                "moderated_at": fields.Datetime.now(),
                "reason": final_reason,
            })
        elif self.action_type == "remove":
            record.write({
                "approval": "removed",
                "moderator_id": self.env.user.id,
                "moderated_at": fields.Datetime.now(),
                "reason": final_reason,
            })
        else:
            raise ValidationError("Invalid action type.")

        return {"type": "ir.actions.act_window_close"}
