from odoo import models, fields, api  # type: ignore


class ModeratorAssignmentSequence(models.Model):
    _name = "moderator_assignment_sequence"
    _description = "Moderator Assignment Sequence Tracking"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    # Attributes
    assignment_count = fields.Integer(default=0)

    # Relationship Attributes
    company_id = fields.Many2one(
        "res.company", required=True, index=True, tracking=True
    )
    group_id = fields.Many2one("res.groups", required=True, tracking=True)
    model_name = fields.Char(
        string="Model Name", required=True, index=True, tracking=True
    )
    last_assigned_user_id = fields.Many2one("res.users", required=True, tracking=True)

    # Model Methods
    @api.model
    def get_or_create_sequence(self, company_id, group_id, model_name):
        """Get existing sequence or create a new one"""
        sequence = self.sudo().search(
            [
                ("company_id", "=", company_id),
                ("group_id", "=", group_id),
                ("model_name", "=", model_name),
            ],
            limit=1,
        )

        if not sequence:
            # Find first moderator for initial assignment
            moderators = (
                self.env["res.users"]
                .sudo()
                .search(
                    [("groups_id", "in", group_id), ("company_id", "=", company_id)],
                    order="id",
                    limit=1,
                )
            )

            default_moderator = moderators[0] if moderators else self.env.user

            sequence = self.sudo().create(
                {
                    "company_id": company_id,
                    "group_id": group_id,
                    "model_name": model_name,
                    "last_assigned_user_id": default_moderator.id,
                    "assignment_count": 0,
                }
            )
        return sequence

    def get_next_moderator(self, moderators):
        """Get the next moderator in round-robin sequence"""
        if not moderators:
            return None

        current_id = self.last_assigned_user_id.id
        moderator_ids = moderators.ids

        if current_id in moderator_ids:
            current_index = moderator_ids.index(current_id)
            next_index = (current_index + 1) % len(moderator_ids)
        else:
            next_index = 0

        return self.env["res.users"].sudo().browse(moderator_ids[next_index])

    def update_sequence(self, moderator_id):
        """Update the sequence with the newly assigned moderator"""
        self.write(
            {
                "last_assigned_user_id": moderator_id.id,
                "assignment_count": self.assignment_count + 1,
            }
        )

    # Constrain
    _sql_constraints = [
        (
            "unique_company_group_model",
            "UNIQUE(company_id, group_id, model_name)",
            "Sequence already exists for this company, group, and model",
        ),
    ]
