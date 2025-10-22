from odoo import models, fields, api  # type: ignore
from odoo.exceptions import AccessError  # type: ignore


class UrgentBuying(models.Model):
    _name = "urgent_buying"
    _description = "Real Estate Feature"
    _inherit = "notify"

    # Attributes
    demand = fields.Text(string="Demand", required=True, tracking=True)
    area = fields.Char(string="Area", required=True, tracking=True)
    finance = fields.Char(string="Finance", required=True, tracking=True)

    # Relationship Attributes
    region_id = fields.Many2one("region",
                                string="Region",
                                required=True,
                                tracking=True)
    district_id = fields.Many2one("district",
                                  string="District",
                                  required=True,
                                  tracking=True)
    reason_buy_id = fields.Many2one("reasons_buy",
                                    string="Reason",
                                    required=True,
                                    tracking=True)
    tag_ids = fields.Many2many(
        "tag",
        string="Tags",
        help="Select or create tags to categorize this post.",
        tracking=True,
    )
    like_user_ids = fields.Many2many(
        "res.users",
        "urgent_buying_like_rel",
        "post_id",
        "user_id",
        string="Users Who Liked",
    )
    view_user_ids = fields.Many2many(
        "res.users",
        "urgent_buying_view_rel",
        "post_id",
        "user_id",
        string="Users Who Viewed",
    )

    # Computed Attribute
    comment_count = fields.Integer(
        string="Comment Count",
        default=0)  # compute in create of realty_comment
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
        self.ensure_one()

        # Check if user has the group
        if not (self.env.user.has_group(
                "realty_bds.access_group_user_urgent_buying") or self.env.user.
                has_group("realty_bds.access_group_realty_urgent_buying")):
            raise AccessError(
                f"You don't have the necessary permissions to like posts.")
        user_id = self.env.uid
        liked_ids = set(self.like_user_ids.ids)
        # If already liked: remove; otherwise add
        if user_id in liked_ids:
            self.sudo().write({"like_user_ids": [(3, user_id)]})
        else:
            self.sudo().write({"like_user_ids": [(4, user_id)]})
        return True

    # Helper method
    def _get_permission_info(self):
        # make a shallow copy to avoid accidentally mutating
        # a dict returned by super() that some other code might rely on
        base = dict(super()._get_permission_info() or {})

        extra = {
            # prefer resolving env.ref at runtime (not at module import time)
            "moderator_group": "realty_bds.access_group_mod_urgent_buying",
            "realty_group": "realty_bds.access_group_realty_urgent_buying",
            "user_group": "realty_bds.access_group_user_urgent_buying",
        }
        base.update(extra)
        return base

    # Constrains
    _sql_constraints = [
        (
            "unique_name",
            "UNIQUE(name)",
            "This name already exists!",
        ),  # Ensure uniqueness
    ]
