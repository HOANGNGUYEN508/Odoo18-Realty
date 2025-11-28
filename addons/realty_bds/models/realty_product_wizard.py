from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError, AccessError, UserError  # type: ignore


class ProductWizard(models.TransientModel):
    _name = "product_wizard"
    _description = "Generic Wizard use for rejecting product with reason"

    # Attributes
    reason = fields.Text(string="Reason", required=True)
    res_model = fields.Char(string="Model Name")
    res_id = fields.Integer(string="Record ID")

    # Selection Attributes
    reject_select = fields.Selection(
        selection="_get_reject_selection",
        string="Reason to Reject",
        help="Choose a predefined reason or 'Other' to enter a custom reason.",
    )

    @api.model
    def _get_reject_selection(self):
        reasons = self.env["reject_reason"].search(
            [("for_type", "=", "property"), ("active", "=", True)]
        )
        return [(reason.name, reason.name) for reason in reasons] + [("other", "Other")]

    @api.onchange("reject_select")
    def _onchange_reject_select(self):
        if self.reject_select and self.reject_select != "other":
            self.reason = self.reject_select
        elif self.reject_select == "other":
            self.reason = False

    def _get_final_reason(self):
        self.ensure_one()
        if self.action_type == "reject":
            return self.reason if self.reject_select == "other" else self.reject_select

    # Action
    def action_confirm(self):
        self.ensure_one()
        final_reason = self._get_final_reason()
        if not final_reason:
            raise ValidationError("Reason is required.")

        group_dict = (
            self.env["permission_tracker"]._get_permission_groups(self.res_model) or {}
        )

        moderator_group = group_dict.get("moderator_group")
        realty_group = group_dict.get("realty_group")
        if not (
            self.env.user.has_group(moderator_group)
            or self.env.user.has_group(realty_group)
        ):
            raise AccessError(
                f"You don't have the necessary permissions to perform this action."
            )

        # Get the target model and record
        target_model = self.env[self.res_model]
        record = target_model.browse(self.res_id)

        record.write(
            {
                "approval": "rejected",
                "moderator_id": self.env.user.id,
                "moderated_at": fields.Datetime.now(),
                "reason": final_reason,
            }
        )

        return {"type": "ir.actions.act_window_close"}
