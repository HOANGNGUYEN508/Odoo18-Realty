from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError, AccessError, UserError  # type: ignore


class CommentWizard(models.TransientModel):
    _name = "comment_wizard"
    _description = "Generic Wizard use for removing comment with reason"

    # Attributes
    reason = fields.Text(string="Reason", required=True)
    res_model = fields.Char(string="Model Name")
    res_id = fields.Integer(string="Record ID")
    comment_id = fields.Char(string="comment ID")

    # Selection Attributes
    remove_select = fields.Selection(
        selection="_get_remove_selection",
        string="Reason to Remove",
        help="Choose a predefined reason or 'Other' to enter a custom reason.",
    )

    @api.model
    def _get_remove_selection(self):
        reasons = self.env["remove_reason"].search(
            [("for_type", "=", "comment"), ("active", "=", True)]
        )

        return [(reason.name, reason.name) for reason in reasons] + [("other", "Other")]

    @api.onchange("remove_select")
    def _onchange_remove_select(self):
        if self.remove_select and self.remove_select != "other":
            self.reason = self.remove_select
        elif self.remove_select == "other":
            self.reason = False

    def _get_final_reason(self):
        self.ensure_one()
        return self.reason if self.remove_select == "other" else self.remove_select

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

        comment = self.env["realty_comment"].browse(self.comment_id).exists()
        if not comment:
            raise UserError(
                "The record no longer exists (deleted by another user). Please exit the form."
            )
        comment.unlink(final_reason)

        return {"type": "ir.actions.act_window_close"}
