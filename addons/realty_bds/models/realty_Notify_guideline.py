from odoo import models, fields, api  # type: ignore
from odoo.exceptions import AccessError  # type: ignore


class Guideline(models.Model):
    _name = "guideline"
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
        "guideline_like_rel",
        "post_id",
        "user_id",
        string="Users Who Liked",
    )
    view_user_ids = fields.Many2many(
        "res.users",
        "guideline_view_rel",
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
    image_urls = fields.Text(string="Image URLs",
                             compute="_compute_image_urls",
                             store=True)

    @api.depends("img_ids")
    def _compute_image_urls(self):
        for rec in self:
            if rec.img_ids:
                urls = []
                for att in rec.img_ids:
                    # Use /web/content_protected endpoint which respects access rights but avoids set public on attachment
                    urls.append("/web/content_protected/%s" % (att.id, ))
                rec.image_urls = ",".join(urls)
            else:
                rec.image_urls = ""

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
                "realty_bds.access_group_user_guideline") or self.env.user.
                has_group("realty_bds.access_group_realty_guideline")):
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
            "moderator_group": "realty_bds.access_group_mod_guideline",
            "realty_group": "realty_bds.access_group_realty_guideline",
            "user_group": "realty_bds.access_group_user_guideline",
        }
        base.update(extra)
        return base

    # Constrains
    _sql_constraints = [
        (
            "unique_name_guideline",
            "UNIQUE(name)",
            "This name already exists!",
        ),  # Ensure uniqueness
    ]
