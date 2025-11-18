from odoo import models, fields, api  # type: ignore
from odoo.exceptions import AccessError, UserError  # type: ignore

class Notification(models.Model):
    _name = "notification"
    _description = "Company Notification"
    _inherit = "notify"

    # Relationship Attributes
    img_ids = fields.Many2many("ir.attachment",
                               string="Images",
                               domain="[('mimetype', 'like', 'image/%')]")
    tag_ids = fields.Many2many(
        "tag",
        string="Tags",
        help="Select or create tags to categorize this post.",
        tracking=True,
    )
    like_user_ids = fields.Many2many(
        "res.users",
        "notification_like_rel",
        "post_id",
        "user_id",
        string="Users Who Liked",
    )
    view_user_ids = fields.Many2many(
        "res.users",
        "notification_view_rel",
        "post_id",
        "user_id",
        string="Users Who Viewed",
    )

    # Computed Attribute
    like_count = fields.Integer(string="Like Count",
                                compute="_compute_like_count",
                                store=True)

    @api.depends("like_user_ids")
    def _compute_like_count(self):
        for post in self:
            post.like_count = len(post.like_user_ids)

    # Action
    def action_toggle_like(self):
        """Add/remove current user from like_user_ids"""
        if not self or not self.exists(): raise UserError("The post no longer exists (deleted by another user). Please refresh the view.")
        self.ensure_one()

        # Check if user has the group
        group_dict = self.env["permission_tracker"]._get_permission_groups(self._name) or {}
        user_group = group_dict.get("user_group")
        realty_group = group_dict.get("realty_group")
        if not (self.env.user.has_group(user_group) or self.env.user.has_group(realty_group)):
            raise AccessError(
                f"You don't have the necessary permissions to like posts.")
        
        user_id = self.env.uid

        # Use toggle command - adds if not present, removes if present
        self.sudo().like_user_ids = [
            (3 if user_id in self.like_user_ids.ids else 4, user_id)
        ]

        return True

    # Constrains
    _sql_constraints = [
        (
            "unique_name",
            "UNIQUE(name)",
            "This name already exists!",
        ),  # Ensure uniqueness
    ]
