from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError, UserError, AccessError  # type: ignore
from odoo.http import request  # type: ignore
import logging

_logger = logging.getLogger(__name__)


class Notify(models.AbstractModel):
    _name = "notify"
    _description = "Realty Abstract Notify - Guideline, Notification, Urgent Buying or Congratulation"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"

    # Attributes
    name = fields.Char(string="Tittle", required=True, help="", tracking=True)
    active = fields.Boolean(string="Active", default=True, tracking=True)
    approval = fields.Selection(
        [
            ("draft", "Draft"),
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("removed", "Removed"),
        ],
        string="Approval",
        default="draft",
        tracking=True,
    )
    reason = fields.Text(
        string="Reason for Rejection/Removal",
        help="Why the post was rejected/removed",
        tracking=True,
    )
    content = fields.Text(string="Content", tracking=True)
    moderated_on = fields.Datetime(string="Moderated On")
    edit_counter = fields.Integer(
        string="Edit Counter",
        default=-1,
        help="Number of times the post can be edited after rejected",
        required=True,
        tracking=True,
    )

    # Relationship Attributes
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    moderator_id = fields.Many2one("res.users",
                                   string="Moderator",
                                   help="User who approved/rejected this post")

    # Action
    def action_open_comments(self):
        self.ensure_one()
        group_dict = self.env["permission_tracker"]._get_permission_groups(
            self._name) or {}
        return {
            "type": "ir.actions.client",
            "tag": "realty_comment_dialog_action",
            "params": {
                "res_model": self._name,
                "res_id": self.id,
                "group": group_dict,
            },
        }

    def action_send(self):
        self.ensure_one()
        if self.create_uid != self.env.user:
            raise UserError(
                "❌ Error: You can only send your own post for approval.")
        if self.approval == "pending":
            raise UserError("❌ Error: Wait for approval.")
        if self.approval != "draft":
            raise UserError(
                "❌ Error: Only posts in 'Draft' state can be send for approval."
            )
        if self.edit_counter != -1:
            raise UserError(
                "❌ Error: This is not the first time you send this.")
        self.approval = "pending"
        self._assign_moderator_after_send()

    def action_resend(self):
        self.ensure_one()
        if self.create_uid != self.env.user:
            raise UserError(
                "❌ Error: You can only send your own post for approval.")
        if self.approval == "pending":
            raise UserError("❌ Error: Wait for approval.")
        if self.approval != "rejected":
            raise UserError(
                "❌ Error: Only posts in 'Rejected' state can be resend for approval."
            )
        if self.edit_counter == 0:
            raise UserError(
                "❌ Error: You have exhausted your edit attempts.")
        self.approval = "pending"
        self._assign_moderator_after_send()

    def action_approve(self):
        self.check_action("approve")

        self.approval = "approved"
        self.moderator_id = self.env.user
        self.moderated_on = fields.Datetime.now()

    def action_reject(self):
        self.check_action("reject")

        # Return action to open the reject wizard
        return {
            "name":
            "Reject Post",
            "type":
            "ir.actions.act_window",
            "res_model":
            "notify_wizard",
            "view_mode":
            "form",
            "views":
            [(self.env.ref("realty_bds.view_generic_wizard_form").id, "form")],
            "target":
            "new",
            "context": {
                "default_action_type": "reject",
                "default_model_name": self._name,  # Pass the model name
                "default_record_id": self.id,  # Pass the record ID
            },
        }

    def action_remove(self):
        self.check_action("remove")

        # Return action to open the remove wizard
        return {
            "name":
            "Remove Post",
            "type":
            "ir.actions.act_window",
            "res_model":
            "notify_wizard",
            "view_mode":
            "form",
            "views":
            [(self.env.ref("realty_bds.view_generic_wizard_form").id, "form")],
            "target":
            "new",
            "context": {
                "default_action_type": "remove",
                "default_model_name": self._name,  # Pass the model name
                "default_record_id": self.id,  # Pass the record ID
            },
        }

    # Helper method
    def check_action(self, action):
        # will later override in child models to use action
        self.ensure_one()

        group_dict = self.env["permission_tracker"]._get_permission_groups(
            self._name) or {}

        moderator_group = group_dict.get("moderator_group")
        realty_group = group_dict.get("realty_group")

        # Check if user has the moderator group
        if not (self.env.user.has_group(moderator_group)
                or self.env.user.has_group(realty_group)):
            raise AccessError(
                f"You don't have the necessary permissions to {action} posts.")

        # Check company permission (pass if user is in access_group_realty_urgent_buying)
        if not self.env.user.has_group(realty_group):
            if self.company_id != self.env.user.company_id and self.company_id.id != 1:
                raise AccessError(
                    f"You can only {action} posts from your own company.")

    def _assign_moderator(self):
        """Assign a moderator using round-robin distribution"""
        company_id = self.env.company.id

        group_dict = self.env["permission_tracker"]._get_permission_groups(
            self._name) or {}

        moderator_group = group_dict.get("moderator_group")

        # Get the moderator group
        group = self.env.ref(moderator_group, raise_if_not_found=False)
        if not group:
            _logger.error(f"Moderator group {moderator_group} not found")
            return None

        # Get moderators for the company and group
        moderators = (self.env["res.users"].sudo().search(
            [("groups_id", "in", group.id), ("company_id", "=", company_id)],
            order="id",
        ))

        if not moderators:
            _logger.warning(
                f"No moderators found for group {group.name} in company {company_id}"
            )
            return None

        # Use advisory lock to prevent race conditions
        lock_key = f"moderator_assignment_{company_id}_{group.id}_{self._name}"
        try:
            self.env.cr.execute("SELECT pg_advisory_xact_lock(hashtext(%s))",
                                (lock_key, ))
        except Exception:
            _logger.exception("Failed to acquire advisory lock for %s",
                              lock_key)
            raise UserError("Could not acquire database lock, try again.")

        # Get or create sequence record for this company, group, and model
        sequence_model = self.env["moderator_assignment_sequence"]
        sequence = sequence_model.get_or_create_sequence(
            company_id, group.id, self._name)

        # Get next moderator
        next_moderator = sequence.get_next_moderator(moderators)
        if next_moderator:
            sequence.update_sequence(next_moderator)
            return next_moderator.id

        return None

    def _assign_moderator_after_send(self):
        """Assign moderator after send/resend - common logic for all child models"""
        moderator_id = self._assign_moderator()
        if moderator_id:
            self.moderator_id = moderator_id
        else:
            _logger.warning(
                f"No moderator assigned for {self._name} post ID {self.id}")

    # Model method
    @api.model_create_multi
    def create(self, vals_list):
        # Enforce single record creation
        if len(vals_list) > 1:
            raise UserError("Only one record can be created at a time.")

        vals = vals_list[0]

        vals["company_id"] = self.env.company.id

        # Create the single record
        record = super().create([vals])
        return record

    def unlink(self):
        # collect attachments before deleting (so we know which records were involved)
        attachments = self.mapped("img_ids")
        rec_ids = self.ids[:]
        model_name = self._name

        # delete the records (this removes the M2M relation rows)
        res = super().unlink()

        # clear res_model/res_id for attachments that pointed to those records
        attachments_to_clear = attachments.filtered(
            lambda a: a.res_model == model_name and a.res_id in rec_ids)
        if attachments_to_clear:
            # use sudo() if your users may not have rights to edit ir.attachment
            attachments_to_clear.sudo().write({
                "res_model": False,
                "res_id": False
            })

        return res

    # Constrains
    @api.constrains("name", "content")
    def _check_name_content(self):
        try:
            reserved_words = self.env["policy"].get_reserved_words()
        except KeyError:
            reserved_words = frozenset()
            _logger.warning(
                "The 'policy' model is not available. No reserved words will be checked."
            )

        for record in self:
            clean_name = record.name.strip().lower() if record.name else ""
            clean_content = record.content.strip().lower(
            ) if record.content else ""
            if not record.name.strip():  # Prevent empty or spaces-only names
                raise ValidationError(
                    "❌ Error: Tittle cannot be empty or contain only spaces!")
            if len(record.name) > 100:  # Limit name length
                raise ValidationError(
                    "❌ Error: Tittle cannot exceed 100 characters!")
            match_name = next((w for w in reserved_words if w in clean_name),
                              None)
            if match_name:
                raise ValidationError(
                    f"❌ Error: Name contains reserved word: '{match_name}'!")
            if len(record.content) > 1000:  # Limit name length
                raise ValidationError(
                    "❌ Error: Content cannot exceed 1000 characters!")
            match_content = next(
                (w for w in reserved_words if w in clean_content), None)
            if match_content:
                raise ValidationError(
                    f"❌ Error: Content contains reserved word: '{match_content}'!"
                )

    @api.constrains("reason", "approval")
    def _check_reason(self):
        for record in self:
            if record.approval == "rejected" and not record.reason:
                raise ValidationError(
                    "❌ Error: Reason for rejection must be provided when the post is rejected."
                )
            if record.approval != "rejected" and record.reason:
                raise ValidationError(
                    "❌ Error: Reason should only be provided when the post is rejected."
                )
