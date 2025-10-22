from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore


class PermissionTracker(models.Model):
    _name = "permission_tracker"
    _description = "Dynamic permission mapping (model -> groups)"

    # Attributes
    model_name = fields.Char(
        string="Model Name",
        required=True,
        index=True,
        help="Technical model name, e.g. 'guideline' or 'realty_comment'",
    )

    # Relationship Attributes
    user_group = fields.Many2one("res.groups", string="User group")
    realty_group = fields.Many2one("res.groups", string="Realty group")
    moderator_group = fields.Many2one("res.groups", string="Moderator group")

    # Model Methods
    @api.model
    def _get_permission_groups(self, model_name):
        """Retrieve the permission groups for a given model name."""
        record = self.sudo().search([("model_name", "=", model_name)], limit=1)
        if not record:
            raise ValidationError(
                f"No permission mapping found for model '{model_name}'."
            )
        return {
            "user_group": f"{model_name}.{record.user_group}",
            "realty_group": f"{model_name}.{record.realty_group}",
            "moderator_group": f"{model_name}.{record.moderator_group}",
        }

    # Constraints
    _sql_constraints = [
        (
            "permission_tracker_model_uniq",
            "unique(model_name)",
            "Mapping for this model already exists.",
        )
    ]
