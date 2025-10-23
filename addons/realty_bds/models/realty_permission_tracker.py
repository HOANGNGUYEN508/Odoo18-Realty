from odoo import models, fields, api, tools  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore


class PermissionTracker(models.Model):
    _name = "permission_tracker"
    _inherit = ["mail.thread", "mail.activity.mixin"]
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
    @tools.ormcache('model_name')
    def _get_permission_groups(self, model_name):
        """Retrieve the permission groups for a given model name - group set up via xml data file."""
        record = self.sudo().search([("model_name", "=", model_name)], limit=1)
        if not record:
            raise ValidationError(
                f"No permission mapping found for model '{model_name}'.")
        
        def _get_xml_id(group):
            if not group:
                return None
            return str(group.get_external_id().get(group.id))
        
        user = _get_xml_id(record.user_group)
        moderator = _get_xml_id(record.moderator_group)
        realty = _get_xml_id(record.realty_group)
        
        return {
            "user_group": user,
            "realty_group": realty,
            "moderator_group": moderator,
        }

    @api.model_create_multi
    def create(self, vals_list):
        # Clear cache before creating new records
        self.clear_caches()
        return super().create(vals_list)

    def write(self, vals):
        # Clear cache before updating records
        self.clear_caches()
        return super().write(vals)

    def unlink(self):
        # Clear cache before deleting records
        self.clear_caches()
        return super().unlink()

    # Constraints
    _sql_constraints = [(
        "permission_tracker_model_uniq",
        "unique(model_name)",
        "Mapping for this model already exists.",
    )]
